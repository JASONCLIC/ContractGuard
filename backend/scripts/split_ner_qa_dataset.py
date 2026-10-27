"""
Split NER-QA SQuAD dataset into contract-level train/test files.

This avoids data leakage by ensuring all QA pairs from the same contract
stay on the same side of the split.

Usage:
    python backend/scripts/split_ner_qa_dataset.py
    python backend/scripts/split_ner_qa_dataset.py --test_ids 6 9 12
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def _extract_contract_ids(paragraph: dict):
    ids = set()
    for qa in paragraph.get("qas", []):
        m = re.match(r"c(\d+)_f.+_q\d+", qa.get("id", ""))
        if m:
            ids.add(int(m.group(1)))
    return ids


def _count_qas(paragraphs):
    return sum(len(p.get("qas", [])) for p in paragraphs)


def _build_payload(version: str, title: str, paragraphs):
    return {
        "version": version,
        "data": [
            {
                "title": title,
                "paragraphs": paragraphs,
            }
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="backend/data/ner_qa_train.json")
    parser.add_argument("--train_out", default="backend/data/ner_qa_train_split.json")
    parser.add_argument("--test_out", default="backend/data/ner_qa_test.json")
    parser.add_argument("--test_ids", type=int, nargs="+", default=[6, 9, 12])
    args = parser.parse_args()

    src = Path(args.input)
    payload = json.loads(src.read_text(encoding="utf-8"))
    version = payload.get("version", "v1.0-contract")
    title = ((payload.get("data") or [{}])[0].get("title") or "ContractGuard NER split")
    paragraphs = ((payload.get("data") or [{}])[0].get("paragraphs") or [])

    by_contract = defaultdict(list)
    skipped = 0
    for p in paragraphs:
        contract_ids = _extract_contract_ids(p)
        if len(contract_ids) != 1:
            skipped += 1
            continue
        contract_id = next(iter(contract_ids))
        by_contract[contract_id].append(p)

    test_ids = set(args.test_ids)
    train_paragraphs = []
    test_paragraphs = []
    for cid in sorted(by_contract.keys()):
        target = test_paragraphs if cid in test_ids else train_paragraphs
        target.extend(by_contract[cid])

    train_payload = _build_payload(version, f"{title} (train split)", train_paragraphs)
    test_payload = _build_payload(version, f"{title} (test split)", test_paragraphs)

    train_out = Path(args.train_out)
    test_out = Path(args.test_out)
    train_out.parent.mkdir(parents=True, exist_ok=True)
    test_out.parent.mkdir(parents=True, exist_ok=True)
    train_out.write_text(json.dumps(train_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    test_out.write_text(json.dumps(test_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    train_contracts = sorted([cid for cid in by_contract.keys() if cid not in test_ids])
    test_contracts = sorted([cid for cid in by_contract.keys() if cid in test_ids])
    print(f"[done] source={src}")
    print(f"[done] train_out={train_out}  contracts={train_contracts}  qas={_count_qas(train_paragraphs)}")
    print(f"[done] test_out={test_out}   contracts={test_contracts}  qas={_count_qas(test_paragraphs)}")
    if skipped:
        print(f"[warn] skipped paragraphs with ambiguous contract ids: {skipped}")


if __name__ == "__main__":
    main()
