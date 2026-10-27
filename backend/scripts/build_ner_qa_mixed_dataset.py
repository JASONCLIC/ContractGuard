"""
Build a mixed NER-QA training dataset with:
1) only 6 core fields
2) configurable real:synthetic ratio (default 1:12)

Output is SQuAD-format JSON compatible with finetune_ner_qa.py.
"""

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


CORE_FIELDS = {
    "party_a",
    "party_b",
    "job_title",
    "work_location",
    "salary_amount",
    "payment_cycle",
}

FIELD_RE = re.compile(r"_f([a-z_]+)_q\d+$")


def _load_squad(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_qas(payload: Dict, source_name: str) -> List[Dict]:
    """
    Flatten SQuAD payload into QA rows while preserving context.
    Keep only core fields and only valid answer spans.
    """
    rows: List[Dict] = []
    for article in payload.get("data", []):
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            if not isinstance(context, str) or not context:
                continue
            for qa in para.get("qas", []):
                qid = qa.get("id", "")
                m = FIELD_RE.search(qid)
                if not m:
                    continue
                field = m.group(1)
                if field not in CORE_FIELDS:
                    continue
                answers = qa.get("answers", [])
                if not isinstance(answers, list) or not answers:
                    continue
                valid_answers = []
                for ans in answers:
                    if not isinstance(ans, dict):
                        continue
                    text = ans.get("text", "")
                    start = ans.get("answer_start", -1)
                    if not isinstance(text, str) or not isinstance(start, int):
                        continue
                    end = start + len(text)
                    if start < 0 or end > len(context):
                        continue
                    if context[start:end] != text:
                        continue
                    valid_answers.append({"text": text, "answer_start": start})
                if not valid_answers:
                    continue
                rows.append(
                    {
                        "source": source_name,
                        "field": field,
                        "context": context,
                        "question": qa.get("question", ""),
                        "answers": valid_answers,
                    }
                )
    return rows


def _group_to_paragraphs(qas: List[Dict], start_contract_id: int = 2000) -> List[Dict]:
    """
    Rebuild paragraphs, grouping by exact context.
    Regenerate ids to keep them unique and canonical.
    """
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for row in qas:
        grouped[row["context"]].append(row)

    paragraphs: List[Dict] = []
    cid = start_contract_id
    q_counter = 0
    for context, rows in grouped.items():
        para_qas = []
        for row in rows:
            q_counter += 1
            para_qas.append(
                {
                    "id": f"c{cid}_f{row['field']}_q{q_counter}",
                    "question": row["question"],
                    "answers": row["answers"],
                    "is_impossible": False,
                }
            )
        paragraphs.append({"context": context, "qas": para_qas})
        cid += 1
    return paragraphs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", default="backend/data/ner_qa_train_split.json")
    parser.add_argument("--synthetic", default="backend/data/ner_qa_synthetic.json")
    parser.add_argument("--generated", default="backend/data/ner_qa_generated.json")
    parser.add_argument("--ratio", type=int, default=12, help="Synthetic per 1 real QA.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="backend/data/ner_qa_train_mix_6f_1to12.json")
    args = parser.parse_args()

    random.seed(args.seed)

    real_rows = _extract_qas(_load_squad(Path(args.real)), "real")
    synth_rows = _extract_qas(_load_squad(Path(args.synthetic)), "synthetic")
    gen_rows = _extract_qas(_load_squad(Path(args.generated)), "generated")
    synth_pool = synth_rows + gen_rows

    if not real_rows:
        raise ValueError("No usable real QA rows found.")
    if not synth_pool:
        raise ValueError("No usable synthetic/generated QA rows found.")

    target_synth = len(real_rows) * max(1, args.ratio)
    actual_synth = min(target_synth, len(synth_pool))
    sampled_synth = random.sample(synth_pool, actual_synth)

    merged_qas = real_rows + sampled_synth
    random.shuffle(merged_qas)

    paragraphs = _group_to_paragraphs(merged_qas)

    output = {
        "version": "v1.0-contract-mixed-6f",
        "data": [
            {
                "title": f"ContractGuard NER mixed dataset (6 fields, real:synthetic=1:{args.ratio})",
                "paragraphs": paragraphs,
            }
        ],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    by_source = {"real": len(real_rows), "synthetic": len(sampled_synth)}
    by_field: Dict[str, int] = defaultdict(int)
    for row in merged_qas:
        by_field[row["field"]] += 1

    print(f"[done] output={out_path}")
    print(f"[done] real={by_source['real']} synthetic={by_source['synthetic']} target_ratio=1:{args.ratio}")
    if actual_synth < target_synth:
        print(
            f"[warn] synthetic pool not enough for strict 1:{args.ratio}; "
            f"used {actual_synth}/{target_synth}."
        )
    print(f"[done] total_qas={len(merged_qas)} paragraphs={len(paragraphs)}")
    print(f"[done] field_distribution={dict(sorted(by_field.items()))}")


if __name__ == "__main__":
    main()
