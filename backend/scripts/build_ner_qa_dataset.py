"""
Build a SQuAD-format QA dataset for fine-tuning the NER QA model.

Sources
-------
1. Contracts stored in the MySQL database (raw_text + key_info)
2. Synthetic contract snippets covering common patterns

Output: backend/data/ner_qa_train.json  (SQuAD v1 format)

Usage
-----
    python backend/scripts/build_ner_qa_dataset.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pymysql

# ── Configuration ──────────────────────────────────────────────────────────
DB = dict(host="127.0.0.1", port=3306, user="root",
          password="zyx41928", database="contractguard", charset="utf8mb4")

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "ner_qa_train.json"

# Field → (question, answer_key_in_key_info)
FIELD_MAP = {
    "job_title":     ("What specific position or role is the employee or intern hired for?",  "job_title"),
    "work_location": ("What is the address of the employee's workplace or office?",           "work_location"),
    "salary_amount": ("What is the exact salary or compensation amount including currency?",  "salary_amount"),
    "payment_cycle": ("How often and on what day is salary paid?",                            "payment_cycle"),
    "party_a":       ("What is the full name of the employer or company?",                    "party_a"),
    "party_b":       ("What is the full name of the employee or intern?",                     "party_b"),
}

# Additional context-specific questions to augment training
EXTRA_QUESTIONS = {
    "job_title": [
        "What position does the employee serve as in this contract?",
        "What is the intern's or employee's job title?",
    ],
    "work_location": [
        "Where will the employee or intern work?",
        "What is the company's office address for the employee's work?",
    ],
    "salary_amount": [
        "How much is the monthly salary stated in GBP, EUR, or USD?",
        "What is the base pay amount in this contract?",
    ],
    "payment_cycle": [
        "On which day of the month is the salary paid?",
        "What is the payment frequency for salary in this contract?",
    ],
    "party_a": [
        "Who is the employer in this agreement?",
        "What company is Party A in this contract?",
    ],
    "party_b": [
        "Who is the employee signing this contract?",
        "What is Party B's name in this agreement?",
    ],
}


def _find_answer_span(context: str, answer: str):
    """Return (start, end) char positions of the first occurrence of answer in context."""
    # Try exact match first
    idx = context.find(answer)
    if idx >= 0:
        return idx, idx + len(answer)
    # Case-insensitive fallback
    idx = context.lower().find(answer.lower())
    if idx >= 0:
        return idx, idx + len(answer)
    return None, None


def build_squad_entry(contract_id: int, title: str, raw_text: str,
                      key_info: dict, qas: list) -> dict:
    """Return a SQuAD-format paragraph dict."""
    return {
        "context": raw_text,
        "qas": qas,
    }


def generate_qas(contract_id: int, raw_text: str, key_info: dict) -> list:
    qas = []
    qa_id = 0

    for field, (primary_q, ki_key) in FIELD_MAP.items():
        answer_text = key_info.get(ki_key, "")
        if not answer_text or answer_text == "Not identified":
            continue

        # Clean answer (strip trailing punctuation / whitespace)
        answer_text = answer_text.strip().rstrip(".,;")

        start, end = _find_answer_span(raw_text, answer_text)
        if start is None:
            # If the stored key_info answer can't be located in raw_text, skip
            continue

        all_questions = [primary_q] + EXTRA_QUESTIONS.get(field, [])
        for question in all_questions:
            qa_id += 1
            qas.append({
                "id": f"c{contract_id}_f{field}_q{qa_id}",
                "question": question,
                "answers": [{"text": answer_text, "answer_start": start}],
                "is_impossible": False,
            })

    return qas


def build_qa_pairs_from_rows(rows, exclude_ids=None):
    """
    Build QA examples from DB rows.  Each row is (id, title, raw_text, key_info_raw).
    Returns (squad_examples, dataset_paragraphs) where squad_examples is a flat list
    of {"question", "context", "answer_text", "answer_start"} dicts suitable for
    finetune_ner_qa.tokenize_examples().
    """
    exclude_ids = set(exclude_ids or [])
    dataset_paragraphs = []
    squad_examples = []
    total_qas = 0

    for contract_id, title, raw_text, key_info_raw in rows:
        if contract_id in exclude_ids:
            continue
        if not raw_text or not key_info_raw:
            continue
        key_info = json.loads(key_info_raw)
        qas = generate_qas(contract_id, raw_text, key_info)
        if not qas:
            continue
        dataset_paragraphs.append({"context": raw_text, "qas": qas})
        total_qas += len(qas)
        for qa in qas:
            for ans in qa["answers"]:
                squad_examples.append({
                    "question":     qa["question"],
                    "context":      raw_text,
                    "answer_text":  ans["text"],
                    "answer_start": ans["answer_start"],
                })
        print(f"  id={contract_id} '{title}': {len(qas)} QA pairs")

    print(f"  Total: {total_qas} QA pairs from {len(dataset_paragraphs)} contracts")
    return squad_examples, dataset_paragraphs


def fetch_contract_rows(exclude_ids=None):
    """Fetch all status='done' contracts from MySQL, optionally excluding IDs."""
    conn = pymysql.connect(**DB)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, raw_text, key_info FROM contracts "
            "WHERE status='done' AND raw_text IS NOT NULL AND key_info IS NOT NULL"
        )
        rows = cur.fetchall()
    conn.close()
    if exclude_ids:
        rows = [r for r in rows if r[0] not in set(exclude_ids)]
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude_ids", type=int, nargs="*", default=[],
                        help="Contract IDs to exclude from the dataset")
    args = parser.parse_args()

    rows = fetch_contract_rows()
    _, dataset_paragraphs = build_qa_pairs_from_rows(rows, exclude_ids=args.exclude_ids)

    squad_data = {
        "version": "v1.0-contract",
        "data": [
            {
                "title": "ContractGuard NER fine-tuning",
                "paragraphs": dataset_paragraphs,
            }
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(squad_data, f, ensure_ascii=False, indent=2)

    n_qas = sum(len(p["qas"]) for p in dataset_paragraphs)
    print(f"\nSaved {n_qas} QA pairs from {len(dataset_paragraphs)} "
          f"contracts → {OUTPUT}")


if __name__ == "__main__":
    main()
