"""
Evaluate QA NER model without retraining.

1) Main: direct QA inference on ner_qa_test.json (out-of-sample)
2) Supplement: end-to-end pipeline on DB contracts (if available)
"""

import json
import re
import sys
import types
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ENTITY_FIELDS = ["party_a", "party_b", "job_title", "work_location", "salary_amount", "payment_cycle"]
ALL_FIELDS_E2E = [
    "contract_name", "party_a", "party_b", "job_title", "work_location",
    "salary_amount", "payment_cycle", "probation", "contract_term",
    "termination_conditions", "breach_liability", "dispute_resolution",
]


def _paths():
    script = Path(__file__).resolve()
    backend = script.parent.parent
    return backend, backend / "data" / "ner_qa_test.json", backend / "models" / "ner_qa_finetuned", backend / "evaluation" / "ner_qa"


def _ensure_package():
    backend, _, _, _ = _paths()
    nlp_dir = backend / "app" / "nlp"
    if "backend" not in sys.modules:
        m = types.ModuleType("backend")
        m.__path__ = [str(backend.parent)]
        sys.modules["backend"] = m
    if "backend.app" not in sys.modules:
        m = types.ModuleType("backend.app")
        m.__path__ = [str(backend / "app")]
        sys.modules["backend.app"] = m
    if "backend.app.nlp" not in sys.modules:
        m = types.ModuleType("backend.app.nlp")
        m.__path__ = [str(nlp_dir)]
        sys.modules["backend.app.nlp"] = m
    return nlp_dir


def _load_module(name: str, file_path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_nlp_modules():
    nlp_dir = _ensure_package()
    _load_module("backend.app.nlp.ner_questions", nlp_dir / "ner_questions.py")
    _load_module("backend.app.nlp.ner_extractor", nlp_dir / "ner_extractor.py")
    cls_mod = _load_module("backend.app.nlp.bert_clause_classifier", nlp_dir / "bert_clause_classifier.py")
    qa_mod = _load_module("backend.app.nlp.ner_qa_extractor", nlp_dir / "ner_qa_extractor.py")
    return cls_mod.BertClauseClassifier, qa_mod.extract_key_info_qa


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def norm_strict(field: str, text: str) -> str:
    _ = field
    return _normalize_spaces(text).lower()


def norm_canonical(field: str, text: str) -> str:
    s = _normalize_spaces(text).lower()
    if not s or s == "not identified":
        return ""
    if field == "salary_amount":
        m = re.search(r"[\d][\d,\.]*", s)
        return m.group(0).replace(",", "") if m else s
    if field == "payment_cycle":
        table = {
            "monthly": ["monthly", "per month", "each month", "按月", "每月"],
            "weekly": ["weekly", "每周", "按周"],
            "biweekly": ["bi-weekly", "biweekly", "fortnightly", "双周"],
            "daily": ["daily", "按日", "每天"],
        }
        for key, vals in table.items():
            if any(v in s for v in vals):
                return key
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "", s)
    return s


def tokens(text: str):
    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text)


def prf(pred: str, gold: str):
    pt, gt = tokens(pred), tokens(gold)
    if not pt and not gt:
        return 1.0, 1.0, 1.0
    if not pt or not gt:
        return 0.0, 0.0, 0.0
    pc, gc = Counter(pt), Counter(gt)
    common = sum((pc & gc).values())
    p = common / max(len(pt), 1)
    r = common / max(len(gt), 1)
    f1 = 0.0 if p + r == 0 else (2 * p * r / (p + r))
    return p, r, f1


def parse_dataset(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for article in raw.get("data", []):
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            for qa in para.get("qas", []):
                qaid = qa.get("id", "")
                m = re.match(r"c(\d+)_f(.+)_q\d+", qaid)
                if not m:
                    continue
                cid, field = m.group(1), m.group(2)
                if field not in ENTITY_FIELDS:
                    continue
                answers = qa.get("answers", [])
                if not answers:
                    continue
                rows.append({
                    "contract_id": cid,
                    "field": field,
                    "question": qa.get("question", ""),
                    "context": context,
                    "gold": answers[0].get("text", ""),
                    "qa_id": qaid,
                })
    return rows


def eval_direct_qa(rows, model_dir: Path):
    from transformers import pipeline
    qa = pipeline("question-answering", model=str(model_dir), tokenizer=str(model_dir), device=-1)
    results = []
    for r in rows:
        pred = ""
        try:
            out = qa(question=r["question"], context=r["context"])
            pred = _normalize_spaces(out.get("answer", ""))
        except Exception:
            pred = ""

        gs = norm_strict(r["field"], r["gold"])
        ps = norm_strict(r["field"], pred)
        gc = norm_canonical(r["field"], r["gold"])
        pc = norm_canonical(r["field"], pred)
        p_s, r_s, f1_s = prf(ps, gs)
        p_c, r_c, f1_c = prf(pc, gc)
        em_s = 1.0 if (gs and ps == gs) else 0.0
        em_c = 1.0 if (gc and pc == gc) else 0.0
        if em_s == 1.0:
            err = "Exact"
        elif not ps:
            err = "Miss"
        elif f1_s > 0:
            err = "Partial"
        else:
            err = "Miss"
        results.append({**r, "pred": pred, "em_s": em_s, "p_s": p_s, "r_s": r_s, "f1_s": f1_s,
                        "em_c": em_c, "p_c": p_c, "r_c": r_c, "f1_c": f1_c, "error_type": err})
    return results


def _avg(x):
    return float(np.mean(x)) if x else 0.0


def summarize(results):
    by_field = {}
    for f in ENTITY_FIELDS:
        rows = [x for x in results if x["field"] == f]
        by_field[f] = {
            "count": len(rows),
            "strict": {"EM": _avg([x["em_s"] for x in rows]), "P": _avg([x["p_s"] for x in rows]),
                       "R": _avg([x["r_s"] for x in rows]), "F1": _avg([x["f1_s"] for x in rows])},
            "canonical": {"EM": _avg([x["em_c"] for x in rows]), "P": _avg([x["p_c"] for x in rows]),
                          "R": _avg([x["r_c"] for x in rows]), "F1": _avg([x["f1_c"] for x in rows])},
            "identification_rate": _avg([1.0 if norm_strict(f, x["pred"]) else 0.0 for x in rows]),
        }

    by_contract = {}
    for cid in sorted({x["contract_id"] for x in results}, key=lambda z: int(z)):
        rows = [x for x in results if x["contract_id"] == cid]
        by_contract[cid] = {
            "count": len(rows),
            "strict_f1_mean": _avg([x["f1_s"] for x in rows]),
            "strict_em_mean": _avg([x["em_s"] for x in rows]),
            "canonical_f1_mean": _avg([x["f1_c"] for x in rows]),
        }

    overall = {
        "strict": {
            "EM": _avg([x["em_s"] for x in results]), "P": _avg([x["p_s"] for x in results]),
            "R": _avg([x["r_s"] for x in results]), "F1": _avg([x["f1_s"] for x in results]),
            "F1_std": float(np.std([x["f1_s"] for x in results])) if results else 0.0,
        },
        "canonical": {
            "EM": _avg([x["em_c"] for x in results]), "P": _avg([x["p_c"] for x in results]),
            "R": _avg([x["r_c"] for x in results]), "F1": _avg([x["f1_c"] for x in results]),
            "F1_std": float(np.std([x["f1_c"] for x in results])) if results else 0.0,
        },
    }
    return {"per_field": by_field, "per_contract": by_contract, "overall": overall}


def _plot_per_field(summary, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fields = ENTITY_FIELDS
    em = [summary["per_field"][f]["strict"]["EM"] for f in fields]
    p = [summary["per_field"][f]["strict"]["P"] for f in fields]
    r = [summary["per_field"][f]["strict"]["R"] for f in fields]
    f1 = [summary["per_field"][f]["strict"]["F1"] for f in fields]
    x, w = np.arange(len(fields)), 0.2
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 1.5 * w, em, w, label="EM")
    ax.bar(x - 0.5 * w, p, w, label="P")
    ax.bar(x + 0.5 * w, r, w, label="R")
    ax.bar(x + 1.5 * w, f1, w, label="F1")
    ax.set_xticks(x); ax.set_xticklabels(fields, rotation=20, ha="right")
    ax.set_ylim(0, 1); ax.set_title("NER-QA Per-Field Metrics (Strict)"); ax.legend()
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_heatmap(results, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    contracts = sorted({x["contract_id"] for x in results}, key=lambda z: int(z))
    mat = np.zeros((len(contracts), len(ENTITY_FIELDS)), dtype=float)
    for i, cid in enumerate(contracts):
        for j, f in enumerate(ENTITY_FIELDS):
            rows = [x["f1_s"] for x in results if x["contract_id"] == cid and x["field"] == f]
            mat[i, j] = _avg(rows)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(mat, cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_xticks(range(len(ENTITY_FIELDS))); ax.set_xticklabels(ENTITY_FIELDS, rotation=20, ha="right")
    ax.set_yticks(range(len(contracts))); ax.set_yticklabels([f"c{c}" for c in contracts])
    ax.set_title("Contract x Field Heatmap (Strict F1)")
    fig.colorbar(im, ax=ax); fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_radar(summary, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["EM", "P", "R", "F1"]
    vals = [summary["overall"]["strict"][k] for k in names]
    ang = np.linspace(0, 2 * np.pi, len(names), endpoint=False).tolist()
    vals += vals[:1]; ang += ang[:1]
    fig = plt.figure(figsize=(6, 6)); ax = fig.add_subplot(111, polar=True)
    ax.plot(ang, vals, linewidth=2); ax.fill(ang, vals, alpha=0.2)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(names); ax.set_ylim(0, 1)
    ax.set_title("NER-QA Overall Radar (Strict)")
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_error_analysis(results, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = Counter([x["error_type"] for x in results])
    labels = ["Exact", "Partial", "Miss"]; vals = [c.get(k, 0) for k in labels]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(vals, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title("Error Type Distribution")
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_identification(summary, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fields = ENTITY_FIELDS
    vals = [summary["per_field"][f]["identification_rate"] for f in fields]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(fields, vals)
    ax.set_ylim(0, 1); ax.set_title("Field Identification Rate")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _segment_clauses(contract_text: str):
    heading_re = re.compile(
        r"((?:Article|Section|Clause)\s+\d+|第[零一二三四五六七八九十百千\d]+条|[（(][一二三四五六七八九十\d]+[）)]|(?<![0-9])[1-9][0-9]{0,1}[.、．](?!\d)|[一二三四五六七八九十]+[、．.])",
        re.IGNORECASE,
    )
    lines = [x.strip() for x in contract_text.splitlines() if x.strip()]
    clauses, cur = [], None
    for line in lines:
        if heading_re.match(line):
            if cur:
                clauses.append(cur)
            cur = {"index_num": len(clauses) + 1, "heading": line[:30], "content": line}
        else:
            if not cur:
                cur = {"index_num": 1, "heading": "Preamble", "content": line}
            else:
                cur["content"] += "\n" + line
    if cur:
        clauses.append(cur)
    if len(clauses) <= 1:
        matches = list(heading_re.finditer(contract_text))
        if len(matches) > 1:
            clauses = []
            for i, m in enumerate(matches):
                s = m.start()
                e = matches[i + 1].start() if i + 1 < len(matches) else len(contract_text)
                chunk = contract_text[s:e].strip()
                if chunk:
                    clauses.append({"index_num": len(clauses) + 1, "heading": chunk[:30], "content": chunk})
    return clauses if clauses else [{"index_num": 1, "heading": "Full", "content": contract_text}]


def eval_e2e(out_dir: Path):
    try:
        import pymysql
    except Exception as exc:
        return {"status": "skipped", "reason": f"pymysql unavailable: {exc}"}
    db = dict(host="127.0.0.1", port=3306, user="root", password="zyx41928", database="contractguard", charset="utf8mb4")
    try:
        conn = pymysql.connect(**db)
        with conn.cursor() as cur:
            cur.execute("SELECT id, raw_text, key_info FROM contracts WHERE status='done' AND raw_text IS NOT NULL AND key_info IS NOT NULL")
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        return {"status": "skipped", "reason": f"DB unavailable: {exc}"}
    if not rows:
        return {"status": "skipped", "reason": "no db contracts"}

    BertClauseClassifier, extract_key_info_qa = _load_nlp_modules()
    detector = BertClauseClassifier()
    recs = []
    for cid, raw_text, key_info_raw in rows:
        try:
            gold = json.loads(key_info_raw) if isinstance(key_info_raw, str) else (key_info_raw or {})
        except Exception:
            gold = {}
        clauses = _segment_clauses(raw_text or "")
        detector.detect(clauses, raw_text or "", contract_type="labor")
        pred = extract_key_info_qa(raw_text or "", clauses=clauses)
        for f in ALL_FIELDS_E2E:
            g = norm_canonical(f, str(gold.get(f, "")))
            p = norm_canonical(f, str(pred.get(f, "")))
            recs.append({"contract_id": cid, "field": f, "em": 1.0 if (g and p == g) else 0.0, "gold": g, "pred": p})
    score = _avg([x["em"] for x in recs]) if recs else 0.0
    result = {"status": "ok", "contracts": len(rows), "field_pairs": len(recs), "e2e_em": score}
    (out_dir / "e2e_report.json").write_text(json.dumps({"summary": result, "rows": recs}, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=None, help="Path to QA evaluation dataset (SQuAD format).")
    parser.add_argument("--model_dir", default=None, help="Path to fine-tuned QA model directory.")
    parser.add_argument("--out_dir", default=None, help="Directory to save evaluation artifacts.")
    args = parser.parse_args()

    backend, data_file, model_dir, out_dir = _paths()
    _ = backend
    if args.data:
        data_file = Path(args.data)
    if args.model_dir:
        model_dir = Path(args.model_dir)
    if args.out_dir:
        out_dir = Path(args.out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = parse_dataset(data_file)
    results = eval_direct_qa(rows, model_dir)
    summary = summarize(results)

    _plot_per_field(summary, out_dir / "ner_qa_per_field.png")
    _plot_heatmap(results, out_dir / "ner_qa_heatmap.png")
    _plot_radar(summary, out_dir / "ner_qa_radar.png")
    _plot_error_analysis(results, out_dir / "ner_qa_error_analysis.png")
    _plot_identification(summary, out_dir / "ner_qa_identification.png")

    e2e_summary = eval_e2e(out_dir)
    payload = {
        "tag": "Out-of-Sample (Held-out Test Data)",
        "qa_pairs": len(results),
        "contracts": len({x["contract_id"] for x in results}),
        "entity_fields": ENTITY_FIELDS,
        "metrics": summary,
        "e2e_db": e2e_summary,
    }
    (out_dir / "metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "predictions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
    print(f"[done] ner_qa evaluation saved to: {out_dir}")


if __name__ == "__main__":
    main()
