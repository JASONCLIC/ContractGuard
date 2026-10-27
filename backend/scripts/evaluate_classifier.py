"""
Evaluate the trained clause classifier without retraining.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

RISK_KEYS = [
    "unilateral_exemption", "excessive_penalty", "vague_termination",
    "probation_period_risk", "wage_payment_unclear", "overtime_leave_unclear",
    "non_compete", "ip_ownership_assignment", "confidentiality",
    "dispute_resolution", "no_risk",
]

SHORT_NAMES = {
    "unilateral_exemption": "Unilateral\nExempt.", "excessive_penalty": "Excessive\nPenalty",
    "vague_termination": "Vague\nTermination", "probation_period_risk": "Probation\nRisk",
    "wage_payment_unclear": "Wage\nUnclear", "overtime_leave_unclear": "Overtime/\nLeave",
    "non_compete": "Non-\nCompete", "ip_ownership_assignment": "IP\nAssign.",
    "confidentiality": "Confiden-\ntiality", "dispute_resolution": "Dispute\nResolut.",
    "no_risk": "No Risk",
}


def _paths():
    script = Path(__file__).resolve()
    backend = script.parent.parent
    return backend, backend / "data", backend / "models" / "clause_classifier", backend / "evaluation" / "classifier"


def _normalize_text_for_split(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _sample_key(sample: dict) -> str:
    norm = _normalize_text_for_split(sample.get("text", ""))
    raw = f"{sample.get('label', 'no_risk')}|{norm}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _deduplicate_samples(samples):
    deduped = []
    seen = set()
    for s in samples:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        key = _sample_key({"text": text, "label": s["label"]})
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"text": text, "label": s["label"]})
    return deduped


def load_squad_as_classification(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = []
    for article in data.get("data", []):
        title = article.get("title", "")
        parts = [p.strip() for p in title.split("-")]
        risk_key = parts[1] if len(parts) >= 2 else None
        for para in article.get("paragraphs", []):
            context = para.get("context", "").strip()
            if not context:
                continue
            for qa in para.get("qas", []):
                is_impossible = qa.get("is_impossible", False)
                label = "no_risk" if is_impossible else (
                    risk_key if (risk_key and risk_key in RISK_KEYS) else "no_risk"
                )
                samples.append({"text": context, "label": label})
    return samples


def load_jsonl(path: Path):
    samples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        label = obj.get("risk_key", obj.get("label", "no_risk"))
        if label not in RISK_KEYS:
            label = "no_risk"
        text = (obj.get("text") or "").strip()
        if text:
            samples.append({"text": text, "label": label})
    return samples


def load_all_samples(data_dir: Path):
    files = [
        ("employment_train.json", "squad"),
        ("cuad_classified.jsonl", "jsonl"),
        ("cuad_synthetic_employment_risks.jsonl", "jsonl"),
        ("cuad_additional_english_training.jsonl", "jsonl"),
    ]
    all_samples, stats = [], {}
    uid = 0
    for name, kind in files:
        path = data_dir / name
        if kind == "squad":
            rows = load_squad_as_classification(path)
        else:
            rows = load_jsonl(path)
        stats[name] = len(rows)
        for r in rows:
            all_samples.append({
                "uid": uid,
                "text": r["text"],
                "label": r["label"],
                "source": name,
            })
            uid += 1
    return all_samples, stats


def _build_antileak_testset(samples, original_eval_split: float):
    from sklearn.model_selection import train_test_split

    train_ref, eval_ref = train_test_split(
        samples,
        test_size=original_eval_split,
        random_state=42,
        stratify=[s["label"] for s in samples],
    )
    train_texts = {s["text"] for s in train_ref}
    clean_eval = [s for s in eval_ref if s["text"] not in train_texts]
    return train_ref, clean_eval


def _plot_confusion_matrix(y_true, y_pred, labels, out_file: Path):
    from sklearn.metrics import confusion_matrix
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cm = confusion_matrix(y_true, y_pred, labels=labels, normalize="true")
    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
    ax.set_xticklabels([SHORT_NAMES.get(x, x) for x in labels], rotation=45, ha="right")
    ax.set_yticklabels([SHORT_NAMES.get(x, x) for x in labels])
    ax.set_title("Normalized Confusion Matrix")
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    fig.colorbar(im, ax=ax); fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_per_class_metrics(report_dict, labels, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = [report_dict.get(lbl, {}).get("precision", 0.0) for lbl in labels]
    r = [report_dict.get(lbl, {}).get("recall", 0.0) for lbl in labels]
    f = [report_dict.get(lbl, {}).get("f1-score", 0.0) for lbl in labels]
    x, w = np.arange(len(labels)), 0.26
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - w, p, w, label="Precision"); ax.bar(x, r, w, label="Recall"); ax.bar(x + w, f, w, label="F1")
    ax.set_xticks(x); ax.set_xticklabels([SHORT_NAMES.get(x, x) for x in labels], rotation=35, ha="right")
    ax.set_ylim(0, 1); ax.set_title("Per-Class P/R/F1"); ax.legend()
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_class_distribution(train_labels, test_labels, labels, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    train_c, test_c = Counter(train_labels), Counter(test_labels)
    train_v = [train_c.get(l, 0) for l in labels]; test_v = [test_c.get(l, 0) for l in labels]
    x, w = np.arange(len(labels)), 0.35
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - w / 2, train_v, w, label="Train"); ax.bar(x + w / 2, test_v, w, label="Test")
    ax.set_xticks(x); ax.set_xticklabels([SHORT_NAMES.get(x, x) for x in labels], rotation=35, ha="right")
    ax.set_title("Class Distribution (Train vs Test)"); ax.legend()
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_balanced_vs_standard(metrics_map, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names, vals = list(metrics_map.keys()), list(metrics_map.values())
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, vals, color=["#4c78a8", "#72b7b2", "#f58518", "#54a24b"])
    ax.set_ylim(0, 1); ax.set_title("Standard vs Imbalance-Aware Metrics")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def _plot_radar(metric_dict, out_file: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(metric_dict.keys()); vals = [metric_dict[k] for k in names]
    angles = np.linspace(0, 2 * np.pi, len(names), endpoint=False).tolist()
    vals += vals[:1]; angles += angles[:1]
    fig = plt.figure(figsize=(6, 6)); ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, vals, linewidth=2); ax.fill(angles, vals, alpha=0.2)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(names); ax.set_ylim(0, 1); ax.set_title("Classifier Radar")
    fig.tight_layout(); fig.savefig(out_file, dpi=160); plt.close(fig)


def evaluate(test_size: float, random_state: int, batch_size: int, anti_leakage: bool,
             original_eval_split: float, out_subdir: str, split_file: str, use_saved_split: bool):
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, classification_report,
        matthews_corrcoef, precision_recall_fscore_support,
    )
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    _, data_dir, model_dir, out_dir = _paths()
    out_dir = out_dir.parent / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    samples, source_stats = load_all_samples(data_dir)
    samples = _deduplicate_samples(samples)

    split_mode = "stratified_holdout"
    split_path = Path(split_file)
    if use_saved_split and split_path.exists():
        payload = json.loads(split_path.read_text(encoding="utf-8"))
        key_to_sample = {_sample_key(s): s for s in samples}
        train_samples = [key_to_sample[k] for k in payload.get("train_keys", []) if k in key_to_sample]
        test_samples = [key_to_sample[k] for k in payload.get("eval_keys", []) if k in key_to_sample]
        if not train_samples or not test_samples:
            raise RuntimeError("Saved split exists but could not map keys to current dataset.")
        split_mode = "saved_split"
    elif anti_leakage:
        train_samples, test_samples = _build_antileak_testset(samples, original_eval_split=original_eval_split)
        if not test_samples:
            raise RuntimeError("Anti-leakage test set is empty after text-overlap filtering.")
        split_mode = "anti_leakage_holdout"
    else:
        from sklearn.model_selection import train_test_split
        train_samples, test_samples = train_test_split(
            samples,
            test_size=test_size,
            random_state=random_state,
            stratify=[s["label"] for s in samples],
        )
    x_train = [s["text"] for s in train_samples]
    y_train = [s["label"] for s in train_samples]
    x_test = [s["text"] for s in test_samples]
    y_test = [s["label"] for s in test_samples]

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to(torch.device("cpu"))
    model.eval()
    id2label = {int(k): v for k, v in model.config.id2label.items()}

    y_pred = []
    for i in range(0, len(x_test), batch_size):
        enc = tokenizer(x_test[i:i + batch_size], truncation=True, max_length=512, padding=True, return_tensors="pt")
        with torch.no_grad():
            logits = model(**enc).logits
        y_pred.extend([id2label.get(i, "no_risk") for i in logits.argmax(dim=-1).cpu().tolist()])

    labels_present = [k for k in RISK_KEYS if k in set(y_test) | set(y_pred)]
    acc = accuracy_score(y_test, y_pred)
    report_str = classification_report(y_test, y_pred, labels=labels_present, zero_division=0)
    report_dict = classification_report(y_test, y_pred, labels=labels_present, zero_division=0, output_dict=True)

    y_true_bin = ["risk" if y != "no_risk" else "no_risk" for y in y_test]
    y_pred_bin = ["risk" if y != "no_risk" else "no_risk" for y in y_pred]
    bin_acc = accuracy_score(y_true_bin, y_pred_bin)
    bal_acc = balanced_accuracy_score(y_true_bin, y_pred_bin)
    mcc = matthews_corrcoef(y_true_bin, y_pred_bin)
    p_risk, r_risk, f_risk, _ = precision_recall_fscore_support(
        y_true_bin, y_pred_bin, labels=["risk"], average="binary", pos_label="risk", zero_division=0
    )
    p_nr, r_nr, f_nr, _ = precision_recall_fscore_support(
        y_true_bin, y_pred_bin, labels=["no_risk"], average="binary", pos_label="no_risk", zero_division=0
    )

    _plot_confusion_matrix(y_test, y_pred, labels_present, out_dir / "confusion_matrix.png")
    _plot_per_class_metrics(report_dict, labels_present, out_dir / "per_class_metrics.png")
    _plot_class_distribution(y_train, y_test, RISK_KEYS, out_dir / "class_distribution.png")
    _plot_balanced_vs_standard({
        "Accuracy": float(bin_acc), "BalancedAcc": float(bal_acc),
        "MacroF1": float(report_dict.get("macro avg", {}).get("f1-score", 0.0)),
        "MCC*": float((mcc + 1.0) / 2.0),
    }, out_dir / "balanced_vs_standard.png")
    _plot_radar({
        "Accuracy": float(acc),
        "Macro-P": float(report_dict.get("macro avg", {}).get("precision", 0.0)),
        "Macro-R": float(report_dict.get("macro avg", {}).get("recall", 0.0)),
        "Macro-F1": float(report_dict.get("macro avg", {}).get("f1-score", 0.0)),
        "MCC*": float((mcc + 1.0) / 2.0),
    }, out_dir / "classifier_radar.png")

    metrics = {
        "dataset_total": len(samples), "dataset_sources": source_stats,
        "evaluation_mode": split_mode,
        "split": {
            "train_size": len(x_train),
            "test_size": len(x_test),
            "test_ratio": (len(x_test) / len(samples)) if samples else 0.0,
            "random_state": random_state,
            "original_eval_split": original_eval_split if anti_leakage else None,
            "split_file": str(split_path) if (use_saved_split and split_path.exists()) else None,
        },
        "multiclass": {
            "accuracy": float(acc),
            "macro_precision": float(report_dict.get("macro avg", {}).get("precision", 0.0)),
            "macro_recall": float(report_dict.get("macro avg", {}).get("recall", 0.0)),
            "macro_f1": float(report_dict.get("macro avg", {}).get("f1-score", 0.0)),
            "weighted_f1": float(report_dict.get("weighted avg", {}).get("f1-score", 0.0)),
        },
        "binary_risk_vs_no_risk": {
            "distribution": {"risk": int(y_true_bin.count("risk")), "no_risk": int(y_true_bin.count("no_risk"))},
            "accuracy": float(bin_acc), "balanced_accuracy": float(bal_acc), "mcc": float(mcc),
            "risk_precision": float(p_risk), "risk_recall": float(r_risk), "risk_f1": float(f_risk),
            "no_risk_precision": float(p_nr), "no_risk_recall": float(r_nr), "no_risk_f1": float(f_nr),
        },
    }
    (out_dir / "classification_report.txt").write_text(f"Accuracy: {acc:.4f}\n\n{report_str}", encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] classifier evaluation saved to: {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--random_state", type=int, default=42)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--anti_leakage", action="store_true",
                        help="Rebuild original 15% holdout and remove text overlap with reconstructed training split.")
    parser.add_argument("--original_eval_split", type=float, default=0.15)
    parser.add_argument("--out_subdir", type=str, default="classifier")
    parser.add_argument("--split_file", type=str, default="backend/data/classifier_split.json")
    parser.add_argument("--no_saved_split", action="store_true",
                        help="Ignore saved split file and fall back to holdout split mode.")
    args = parser.parse_args()
    evaluate(
        args.test_size,
        args.random_state,
        args.batch_size,
        args.anti_leakage,
        args.original_eval_split,
        args.out_subdir,
        args.split_file,
        not args.no_saved_split,
    )


if __name__ == "__main__":
    main()
