"""
Fine-tune deepset/roberta-base-squad2 on contract-specific QA data.

Key fix vs naive approach
─────────────────────────
Contract texts are long (1000-5000+ chars > 512-token limit).
We use a sliding-window tokenizer with stride so the answer always
falls within at least one window, and skip windows where the answer
is truncated.  This follows the official HF SQuAD fine-tuning recipe.

Usage
-----
    python backend/scripts/finetune_ner_qa.py \
        --data  backend/data/ner_qa_train_split.json \
        --eval_data backend/data/ner_qa_test.json \
        --output backend/models/ner_qa_finetuned \
        --epochs 3

After training, update ner_qa_extractor.py:
    _MODEL_NAME = "backend/models/ner_qa_finetuned"
"""

import argparse
import inspect
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForQuestionAnswering,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator,
)

BASE_MODEL = "deepset/roberta-base-squad2"
MAX_LENGTH = 384
DOC_STRIDE = 128


# ── Dataset ───────────────────────────────────────────────────────────────────

class ContractQADataset(Dataset):
    def __init__(self, features):
        self.features = features

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        f = self.features[idx]
        return {
            "input_ids":      torch.tensor(f["input_ids"],      dtype=torch.long),
            "attention_mask": torch.tensor(f["attention_mask"], dtype=torch.long),
            "start_positions": torch.tensor(f["start_positions"], dtype=torch.long),
            "end_positions":   torch.tensor(f["end_positions"],   dtype=torch.long),
        }


# ── Data loading ──────────────────────────────────────────────────────────────

def load_squad_data(path: str):
    """Load SQuAD-format JSON; return list of (question, context, answer_text, answer_start)."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    examples = []
    for article in raw["data"]:
        for para in article["paragraphs"]:
            context = para["context"]
            for qa in para["qas"]:
                if qa.get("is_impossible"):
                    continue
                for ans in qa["answers"]:
                    examples.append({
                        "question":     qa["question"],
                        "context":      context,
                        "answer_text":  ans["text"],
                        "answer_start": ans["answer_start"],
                    })
    return examples


# ── Sliding-window tokenization ────────────────────────────────────────────────

def tokenize_examples(examples, tokenizer):
    """
    Tokenize with a sliding window so long contexts are handled correctly.
    Skips windows where the answer is truncated.
    """
    features = []
    skipped  = 0

    for ex in examples:
        question     = ex["question"]
        context      = ex["context"]
        answer_text  = ex["answer_text"]
        answer_start = ex["answer_start"]
        answer_end   = answer_start + len(answer_text)

        # Tokenize with overflow (sliding windows)
        enc = tokenizer(
            question,
            context,
            truncation="only_second",
            max_length=MAX_LENGTH,
            stride=DOC_STRIDE,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
        )

        # offset_mapping maps each token to (char_start, char_end) in the ORIGINAL strings.
        # For pair encodings, tokens from the first sequence (question) have valid offsets
        # in sequence 0; tokens from the second sequence (context) have valid offsets in
        # sequence 1.  We use `sequence_ids` to distinguish them.
        sequence_ids_per_window = enc.sequence_ids  # list for single; we'll iterate

        # Handle both single-window and multi-window (overflowing) cases
        n_windows = len(enc["input_ids"])
        for w in range(n_windows):
            offset_mapping = enc["offset_mapping"][w]
            seq_ids        = enc.sequence_ids(w)

            # Token indices that belong to the context (sequence 1)
            context_start_tok = next(
                (i for i, s in enumerate(seq_ids) if s == 1), None)
            context_end_tok = (
                len(seq_ids) - 1 -
                next((i for i, s in enumerate(reversed(seq_ids)) if s == 1), 0)
            )
            if context_start_tok is None:
                skipped += 1
                continue

            # Char span covered by this window's context tokens
            win_char_start = offset_mapping[context_start_tok][0]
            win_char_end   = offset_mapping[context_end_tok][1]

            # Skip if answer is fully outside this window
            if answer_end <= win_char_start or answer_start >= win_char_end:
                skipped += 1
                continue

            # Find start token
            start_tok = None
            for i in range(context_start_tok, context_end_tok + 1):
                if offset_mapping[i][0] <= answer_start < offset_mapping[i][1]:
                    start_tok = i
                    break

            # Find end token
            end_tok = None
            for i in range(context_end_tok, context_start_tok - 1, -1):
                if offset_mapping[i][0] < answer_end <= offset_mapping[i][1]:
                    end_tok = i
                    break

            if start_tok is None or end_tok is None:
                skipped += 1
                continue

            features.append({
                "input_ids":       enc["input_ids"][w],
                "attention_mask":  enc["attention_mask"][w],
                "start_positions": start_tok,
                "end_positions":   end_tok,
            })

    print(f"  Tokenized: {len(features)} windows kept, {skipped} skipped (answer outside window)")
    return features


def _build_dataset_from_examples(examples, tokenizer):
    features = tokenize_examples(examples, tokenizer)
    if not features:
        raise ValueError("No valid tokenized windows produced from the given examples.")
    return ContractQADataset(features), len(features)


# ── Reusable training function ────────────────────────────────────────────────

def train_qa_model(
    examples,
    output_dir,
    base_model=BASE_MODEL,
    epochs=3,
    lr=2e-5,
    batch_size=4,
    eval_examples=None,
    quiet=False,
):
    """
    Fine-tune a QA model from *base_model* on the given *examples*.

    Parameters
    ----------
    examples : list[dict]
        Each dict has keys: question, context, answer_text, answer_start.
    output_dir : str or Path
        Directory to save the fine-tuned model + tokenizer.
    base_model : str
        HuggingFace model name or local path to start from.
    quiet : bool
        If True, suppress most print output (useful in LOOCV loops).

    Returns
    -------
    (model, tokenizer) – the fine-tuned model and its tokenizer.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    dataset, num_train_windows = _build_dataset_from_examples(examples, tokenizer)
    eval_dataset = None
    num_eval_windows = 0
    if eval_examples:
        eval_dataset, num_eval_windows = _build_dataset_from_examples(eval_examples, tokenizer)
    model = AutoModelForQuestionAnswering.from_pretrained(base_model)

    args_kwargs = {
        "output_dir": str(output_dir),
        "num_train_epochs": epochs,
        "per_device_train_batch_size": batch_size,
        "learning_rate": lr,
        "warmup_steps": max(10, num_train_windows // 10),
        "weight_decay": 0.01,
        "logging_dir": str(output_dir / "logs"),
        "logging_steps": 50 if quiet else 10,
        "save_strategy": "no",
        "no_cuda": True,
        "report_to": "none",
        "disable_tqdm": quiet,
    }

    # Backward/forward compatibility across transformers versions:
    # some versions use `evaluation_strategy`, some `eval_strategy`,
    # and very old versions support neither.
    ta_params = inspect.signature(TrainingArguments.__init__).parameters
    if eval_dataset is not None:
        if "evaluation_strategy" in ta_params:
            args_kwargs["evaluation_strategy"] = "epoch"
        elif "eval_strategy" in ta_params:
            args_kwargs["eval_strategy"] = "epoch"

    training_args = TrainingArguments(**args_kwargs)

    import logging
    if quiet:
        logging.getLogger("transformers").setLevel(logging.ERROR)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
    )

    if not quiet:
        print(f"Fine-tuning {base_model} for {epochs} epochs "
              f"({num_train_windows} train windows, {num_eval_windows} eval windows) …")
    trainer.train()

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    if quiet:
        logging.getLogger("transformers").setLevel(logging.WARNING)

    return model, tokenizer


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",       default="backend/data/ner_qa_train_split.json")
    parser.add_argument("--eval_data",  default="backend/data/ner_qa_test.json")
    parser.add_argument("--output",     default="backend/models/ner_qa_finetuned")
    parser.add_argument("--epochs",     type=int,   default=3)
    parser.add_argument("--batch_size", type=int,   default=4)
    parser.add_argument("--lr",         type=float, default=2e-5)
    args = parser.parse_args()

    print(f"Loading data from {args.data}")
    examples = load_squad_data(args.data)
    print(f"  {len(examples)} raw QA examples")
    eval_examples = []
    if args.eval_data and Path(args.eval_data).exists():
        print(f"Loading eval data from {args.eval_data}")
        eval_examples = load_squad_data(args.eval_data)
        print(f"  {len(eval_examples)} raw eval QA examples")
    elif args.eval_data:
        print(f"[warn] Eval data not found: {args.eval_data} (training without eval set)")

    if not examples:
        print("No training data. Run build_ner_qa_dataset.py first.")
        sys.exit(1)

    model, tokenizer = train_qa_model(
        examples,
        output_dir=args.output,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        eval_examples=eval_examples,
    )

    print(f"\nDone. Model saved → {Path(args.output).resolve()}")
    print(f"Set in ner_qa_extractor.py:")
    print(f'  _MODEL_NAME = "{Path(args.output).resolve()}"')


if __name__ == "__main__":
    main()
