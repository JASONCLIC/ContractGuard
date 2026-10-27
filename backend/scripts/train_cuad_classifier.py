"""
Train a BERT sequence classifier for employment contract risk detection.
(Plan B: classification approach, no gated model required)

Data sources:
  1. backend/data/employment_train.json                       (SQuAD v2 → classification, ~120)
  2. backend/data/cuad_classified.jsonl                       (CUAD-sourced samples, ~800)
  3. backend/data/cuad_synthetic_employment_risks.jsonl       (4 synthetic employment labels, ~200)
  4. backend/data/cuad_additional_english_training.jsonl      (CUAD-covered labels, ~100)

Output:
  backend/models/clause_classifier/   (bert-base-uncased fine-tuned)
  backend/evaluation/                 (confusion_matrix.png, per_class_metrics.png, reports)

Usage:
  python backend/scripts/train_cuad_classifier.py
  python backend/scripts/train_cuad_classifier.py --epochs 4 --learning_rate 3e-5 --kfold 5
  python backend/scripts/train_cuad_classifier.py --kfold 0   # skip cross-validation
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import numpy as np

RISK_KEYS = [
    "unilateral_exemption",
    "excessive_penalty",
    "vague_termination",
    "probation_period_risk",
    "wage_payment_unclear",
    "overtime_leave_unclear",
    "non_compete",
    "ip_ownership_assignment",
    "confidentiality",
    "dispute_resolution",
    "no_risk",
]

SHORT_NAMES = {
    "unilateral_exemption":   "Unilateral\nExempt.",
    "excessive_penalty":      "Excessive\nPenalty",
    "vague_termination":      "Vague\nTermination",
    "probation_period_risk":  "Probation\nRisk",
    "wage_payment_unclear":   "Wage\nUnclear",
    "overtime_leave_unclear": "Overtime/\nLeave",
    "non_compete":            "Non-\nCompete",
    "ip_ownership_assignment":"IP\nAssign.",
    "confidentiality":        "Confiden-\ntiality",
    "dispute_resolution":     "Dispute\nResolut.",
    "no_risk":                "No Risk",
}


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_squad_as_classification(path: Path):
    """Convert SQuAD v2 format to (text, label) pairs."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
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
    """Load any classification jsonl with 'text' + 'risk_key' fields."""
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            risk_key = obj.get("risk_key", obj.get("label", "no_risk"))
            if risk_key not in RISK_KEYS:
                risk_key = "no_risk"
            samples.append({"text": obj["text"], "label": risk_key})
    return samples


def _normalize_text_for_split(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _sample_key(sample: dict) -> str:
    norm = _normalize_text_for_split(sample.get("text", ""))
    raw = f"{sample.get('label', 'no_risk')}|{norm}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _deduplicate_samples(samples):
    deduped = []
    seen = set()
    dropped = 0
    for s in samples:
        text = (s.get("text") or "").strip()
        if not text:
            dropped += 1
            continue
        key = _sample_key({"text": text, "label": s["label"]})
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        deduped.append({"text": text, "label": s["label"]})
    return deduped, dropped


# ── Evaluation helpers ─────────────────────────────────────────────────────────

def run_evaluation(model, tokenizer, test_samples, label2id, id2label,
                   out_dir: Path, max_length: int = 512,
                   train_samples=None):
    """Run metrics + generate charts on the held-out test split.

    Parameters
    ----------
    train_samples : list[dict] | None
        If provided, used to generate the class distribution comparison chart.
    """
    import torch
    import numpy as np
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, classification_report,
        confusion_matrix, matthews_corrcoef, precision_recall_fscore_support,
    )
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    device = torch.device("cpu")
    model = model.to(device)
    texts  = [s["text"]  for s in test_samples]
    y_true = [s["label"] for s in test_samples]

    y_pred = []
    batch_size = 16
    model.eval()
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        enc = tokenizer(
            batch, truncation=True, max_length=max_length,
            padding=True, return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        best = logits.argmax(dim=-1).cpu().tolist()
        y_pred.extend([id2label.get(b, "no_risk") for b in best])

    labels_present = sorted(set(y_true + y_pred),
                            key=lambda k: RISK_KEYS.index(k) if k in RISK_KEYS else 999)
    acc = accuracy_score(y_true, y_pred)

    # ── Classification report ──────────────────────────────────────────────────
    report_str  = classification_report(y_true, y_pred, labels=labels_present, zero_division=0)
    report_dict = classification_report(y_true, y_pred, labels=labels_present,
                                        zero_division=0, output_dict=True)

    print("\n" + "=" * 60)
    print("  CLASSIFICATION METRICS")
    print("=" * 60)
    print(f"  Accuracy: {acc:.4f}  ({acc:.1%})")
    print()
    print(report_str)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "classification_report.txt").write_text(
        f"Accuracy: {acc:.4f}\n\n{report_str}", encoding="utf-8"
    )

    # ── Binary risk detection metrics (enhanced) ──────────────────────────────
    y_true_bin = ["risk" if y != "no_risk" else "no_risk" for y in y_true]
    y_pred_bin = ["risk" if y != "no_risk" else "no_risk" for y in y_pred]
    n_risk = y_true_bin.count("risk")
    n_norisk = y_true_bin.count("no_risk")

    bin_acc  = accuracy_score(y_true_bin, y_pred_bin)
    bal_acc  = balanced_accuracy_score(y_true_bin, y_pred_bin)
    mcc      = matthews_corrcoef(y_true_bin, y_pred_bin)

    p_risk, r_risk, f_risk, _ = precision_recall_fscore_support(
        y_true_bin, y_pred_bin, labels=["risk"],
        average="binary", pos_label="risk", zero_division=0,
    )
    p_norisk, r_norisk, f_norisk, _ = precision_recall_fscore_support(
        y_true_bin, y_pred_bin, labels=["no_risk"],
        average="binary", pos_label="no_risk", zero_division=0,
    )

    print("=" * 60)
    print("  RISK DETECTION METRICS  (binary: risk vs no_risk)")
    print("=" * 60)
    print(f"  Distribution : risk={n_risk} ({n_risk/len(y_true_bin):.1%})"
          f" | no_risk={n_norisk} ({n_norisk/len(y_true_bin):.1%})")
    print(f"  Accuracy          : {bin_acc:.4f}")
    print(f"  Balanced Accuracy : {bal_acc:.4f}")
    print(f"  MCC               : {mcc:.4f}")
    print(f"  ---")
    print(f"           Precision  Recall  F1")
    print(f"  risk       {p_risk:.4f}   {r_risk:.4f}  {f_risk:.4f}")
    print(f"  no_risk    {p_norisk:.4f}   {r_norisk:.4f}  {f_norisk:.4f}")
    print("=" * 60 + "\n")

    bin_report = (
        f"Binary Risk Detection (risk vs no_risk)\n"
        f"Distribution: risk={n_risk} ({n_risk/len(y_true_bin):.1%})"
        f" | no_risk={n_norisk} ({n_norisk/len(y_true_bin):.1%})\n"
        f"{'─' * 40}\n"
        f"Accuracy          : {bin_acc:.4f}\n"
        f"Balanced Accuracy : {bal_acc:.4f}\n"
        f"MCC               : {mcc:.4f}\n"
        f"{'─' * 40}\n"
        f"{'':>10}Precision  Recall  F1\n"
        f"risk       {p_risk:.4f}   {r_risk:.4f}  {f_risk:.4f}\n"
        f"no_risk    {p_norisk:.4f}   {r_norisk:.4f}  {f_norisk:.4f}\n"
    )
    (out_dir / "risk_detection_metrics.txt").write_text(bin_report, encoding="utf-8")

    # ── Confusion matrix ───────────────────────────────────────────────────────
    cm = confusion_matrix(y_true, y_pred, labels=labels_present)
    cm_norm = cm.astype(float)
    row_sums = cm_norm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_norm /= row_sums

    n = len(labels_present)
    short = [SHORT_NAMES.get(c, c) for c in labels_present]
    fig, ax = plt.subplots(figsize=(max(10, n * 1.1), max(8, n * 0.9)))
    im = ax.imshow(cm_norm, interpolation="nearest", cmap="Blues", vmin=0, vmax=1)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Row-normalised")
    ticks = np.arange(n)
    ax.set_xticks(ticks); ax.set_xticklabels(short, fontsize=8, ha="center")
    ax.set_yticks(ticks); ax.set_yticklabels(short, fontsize=8)
    for i in range(n):
        for j in range(n):
            cnt = int(cm[i, j])
            if cnt == 0:
                continue
            color = "white" if cm_norm[i, j] > 0.5 else "black"
            ax.text(j, i, f"{cnt}\n({cm_norm[i,j]:.0%})",
                    ha="center", va="center", fontsize=7, color=color)
    ax.set_xlabel("Predicted Label", fontsize=11, labelpad=10)
    ax.set_ylabel("True Label",      fontsize=11, labelpad=10)
    ax.set_title("Clause Risk Classifier — Confusion Matrix", fontsize=13, pad=14)
    fig.tight_layout()
    cm_path = out_dir / "confusion_matrix.png"
    fig.savefig(str(cm_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[eval] Confusion matrix   → {cm_path}")

    # ── Per-class bar chart ────────────────────────────────────────────────────
    classes = [k for k in RISK_KEYS if k in report_dict]
    prec_vals = [report_dict[c]["precision"] for c in classes]
    rec_vals  = [report_dict[c]["recall"]    for c in classes]
    f1_vals   = [report_dict[c]["f1-score"]  for c in classes]
    short_bar = [SHORT_NAMES.get(c, c).replace("\n", " ") for c in classes]

    x = np.arange(len(classes))
    w = 0.25
    fig2, ax2 = plt.subplots(figsize=(max(12, len(classes) * 1.4), 5))
    ax2.bar(x - w, prec_vals, w, label="Precision", color="#4C72B0")
    ax2.bar(x,     rec_vals,  w, label="Recall",    color="#DD8452")
    ax2.bar(x + w, f1_vals,   w, label="F1-score",  color="#55A868")
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_bar, fontsize=9, rotation=30, ha="right")
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel("Score"); ax2.set_title("Per-Class Precision / Recall / F1-score", fontsize=12)
    ax2.legend(); ax2.grid(axis="y", alpha=0.4)
    fig2.tight_layout()
    bar_path = out_dir / "per_class_metrics.png"
    fig2.savefig(str(bar_path), dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"[eval] Per-class bar chart → {bar_path}")

    # ── NEW: Class distribution chart ─────────────────────────────────────────
    if train_samples is not None:
        _plot_class_distribution(train_samples, test_samples, out_dir)

    # ── NEW: Balanced vs Standard metrics chart ───────────────────────────────
    _plot_balanced_vs_standard(
        acc, bal_acc, f_risk, mcc, out_dir
    )

    print(f"\n[eval] All outputs written to: {out_dir}")


def _plot_class_distribution(train_samples, test_samples, out_dir):
    """Chart: class distribution comparison between train and test sets."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    train_labels = [s["label"] for s in train_samples]
    test_labels  = [s["label"] for s in test_samples]

    train_counts = {k: 0 for k in RISK_KEYS}
    test_counts  = {k: 0 for k in RISK_KEYS}
    for l in train_labels:
        train_counts[l] = train_counts.get(l, 0) + 1
    for l in test_labels:
        test_counts[l] = test_counts.get(l, 0) + 1

    classes = RISK_KEYS
    train_pct = [train_counts[c] / len(train_labels) * 100 for c in classes]
    test_pct  = [test_counts[c]  / len(test_labels)  * 100 for c in classes]
    short_bar = [SHORT_NAMES.get(c, c).replace("\n", " ") for c in classes]

    x = np.arange(len(classes))
    w = 0.35

    fig, ax = plt.subplots(figsize=(max(12, len(classes) * 1.4), 5))
    fig.patch.set_facecolor("#F0F0FA")
    ax.set_facecolor("#F8F8FF")

    b1 = ax.bar(x - w/2, train_pct, w,
                label=f"Train (n={len(train_labels)})", color="#4C72B0", alpha=0.85)
    b2 = ax.bar(x + w/2, test_pct,  w,
                label=f"Test (n={len(test_labels)})",   color="#DD8452", alpha=0.85)

    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                        f"{h:.1f}%", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(short_bar, fontsize=9, rotation=30, ha="right")
    ax.set_ylabel("Proportion (%)", fontsize=11)
    ax.set_title("Class Distribution — Train vs Test", fontsize=13,
                 fontweight="bold", pad=14)
    ax.legend(fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()

    out = out_dir / "class_distribution.png"
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[eval] Class distribution  → {out}")


def _plot_balanced_vs_standard(acc, bal_acc, f1, mcc, out_dir):
    """Chart: standard metrics vs imbalance-aware metrics side by side."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    labels    = ["Accuracy\nvs\nBalanced Acc.", "F1 (risk)\nvs\nMCC"]
    standard  = [acc,     f1]
    balanced  = [bal_acc, mcc]

    x = np.arange(len(labels))
    w = 0.3

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#F0F0FA")
    ax.set_facecolor("#F8F8FF")

    b1 = ax.bar(x - w/2, standard, w, label="Standard Metric",
                color="#4C72B0", alpha=0.85)
    b2 = ax.bar(x + w/2, balanced, w, label="Imbalance-Aware Metric",
                color="#55A868", alpha=0.85)

    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                    f"{h:.4f}", ha="center", va="bottom", fontsize=10,
                    fontweight="bold")

    for i in range(len(labels)):
        diff = balanced[i] - standard[i]
        mid_y = max(standard[i], balanced[i]) + 0.06
        ax.annotate(
            f"{diff:+.4f}", xy=(x[i], mid_y),
            ha="center", va="bottom", fontsize=9,
            color="#D32F2F" if diff < 0 else "#388E3C",
            fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=11)
    ax.set_title("Standard vs Imbalance-Aware Metrics (Binary Risk Detection)",
                 fontsize=12, fontweight="bold", pad=14)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()

    out = out_dir / "balanced_vs_standard.png"
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[eval] Balanced vs std     → {out}")


# ── K-Fold cross-validation ────────────────────────────────────────────────────

def run_kfold(all_samples, label2id, id2label, args, out_dir: Path):
    """
    Stratified K-Fold cross-validation.
    Each fold: train a fresh model from args.model_name, evaluate on held-out fold.
    Outputs:
      - Console summary table
      - backend/evaluation/kfold_summary.txt
      - backend/evaluation/kfold_per_class.png   (per-class F1 across folds)
      - backend/evaluation/kfold_fold_acc.png    (accuracy per fold bar chart)
    """
    from datasets import Dataset
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import (
        accuracy_score, classification_report,
        precision_recall_fscore_support,
    )
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    k = args.kfold
    print(f"\n{'='*60}")
    print(f"  {k}-FOLD CROSS-VALIDATION  (epochs={args.epochs}, lr={args.learning_rate})")
    print(f"{'='*60}")

    texts  = [s["text"]  for s in all_samples]
    labels = [s["label"] for s in all_samples]

    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)

    fold_results = []   # list of per-fold dicts

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(texts, labels), start=1):
        print(f"\n[fold {fold_idx}/{k}] train={len(train_idx)}  val={len(val_idx)}")

        train_s = [all_samples[i] for i in train_idx]
        val_s   = [all_samples[i] for i in val_idx]

        tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)

        def _tok(batch):
            return tokenizer(batch["text"], truncation=True, max_length=args.max_length)

        train_ds = Dataset.from_dict({
            "text":   [s["text"]  for s in train_s],
            "labels": [label2id[s["label"]] for s in train_s],
        }).map(_tok, batched=True, remove_columns=["text"])

        collator = DataCollatorWithPadding(tokenizer=tokenizer)

        fold_model = AutoModelForSequenceClassification.from_pretrained(
            args.model_name,
            num_labels=len(RISK_KEYS),
            id2label=id2label,
            label2id=label2id,
        )

        fold_dir = out_dir / f"kfold_fold{fold_idx}"
        targs = TrainingArguments(
            output_dir=str(fold_dir),
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            warmup_ratio=args.warmup_ratio,
            weight_decay=0.01,
            logging_steps=20,
            save_strategy="no",
            fp16=False,
            no_cuda=True,
            report_to=[],
            dataloader_num_workers=0,
        )
        trainer = Trainer(
            model=fold_model,
            args=targs,
            train_dataset=train_ds,
            data_collator=collator,
        )
        trainer.train()

        # ── Inference on val fold ──────────────────────────────────────────────
        import torch
        fold_model.eval()
        val_texts  = [s["text"]  for s in val_s]
        val_y_true = [s["label"] for s in val_s]
        val_y_pred = []
        for i in range(0, len(val_texts), 16):
            batch = val_texts[i: i + 16]
            enc = tokenizer(batch, truncation=True, max_length=args.max_length,
                            padding=True, return_tensors="pt")
            with torch.no_grad():
                logits = fold_model(**enc).logits
            preds = logits.argmax(dim=-1).cpu().tolist()
            val_y_pred.extend([id2label.get(p, "no_risk") for p in preds])

        acc = accuracy_score(val_y_true, val_y_pred)
        report = classification_report(
            val_y_true, val_y_pred,
            labels=RISK_KEYS, zero_division=0, output_dict=True,
        )
        p_bin, r_bin, f_bin, _ = precision_recall_fscore_support(
            ["risk" if y != "no_risk" else "no_risk" for y in val_y_true],
            ["risk" if y != "no_risk" else "no_risk" for y in val_y_pred],
            labels=["risk"], average="binary", pos_label="risk", zero_division=0,
        )

        fold_results.append({
            "fold":    fold_idx,
            "acc":     acc,
            "macro_p": report["macro avg"]["precision"],
            "macro_r": report["macro avg"]["recall"],
            "macro_f": report["macro avg"]["f1-score"],
            "bin_f1":  f_bin,
            "per_class_f1": {k: report[k]["f1-score"] for k in RISK_KEYS if k in report},
        })
        print(f"  Accuracy={acc:.4f}  Macro-F1={report['macro avg']['f1-score']:.4f}"
              f"  BinaryF1={f_bin:.4f}")

        # Free memory
        del fold_model, trainer
        import gc; gc.collect()

    # ── Summary table ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  {k}-FOLD SUMMARY")
    print(f"{'='*60}")
    header = f"{'Fold':>5} | {'Accuracy':>9} | {'Macro-P':>8} | {'Macro-R':>8} | {'Macro-F1':>9} | {'Binary-F1':>10}"
    print(header)
    print("-" * len(header))
    for r in fold_results:
        print(f"{r['fold']:>5} | {r['acc']:>9.4f} | {r['macro_p']:>8.4f} | "
              f"{r['macro_r']:>8.4f} | {r['macro_f']:>9.4f} | {r['bin_f1']:>10.4f}")
    print("-" * len(header))

    mean_acc    = np.mean([r["acc"]     for r in fold_results])
    mean_mf1    = np.mean([r["macro_f"] for r in fold_results])
    mean_bf1    = np.mean([r["bin_f1"]  for r in fold_results])
    std_acc     = np.std( [r["acc"]     for r in fold_results])
    std_mf1     = np.std( [r["macro_f"] for r in fold_results])

    print(f"{'Mean':>5} | {mean_acc:>9.4f} | {'':>8} | {'':>8} | {mean_mf1:>9.4f} | {mean_bf1:>10.4f}")
    print(f"{'Std':>5} | {std_acc:>9.4f} | {'':>8} | {'':>8} | {std_mf1:>9.4f} |")
    print(f"{'='*60}\n")

    # ── Save text report ───────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{k}-Fold Cross-Validation Summary",
        f"Model: {args.model_name}  |  Epochs: {args.epochs}  |  LR: {args.learning_rate}",
        "=" * 70,
        header,
        "-" * len(header),
    ]
    for r in fold_results:
        lines.append(f"{r['fold']:>5} | {r['acc']:>9.4f} | {r['macro_p']:>8.4f} | "
                     f"{r['macro_r']:>8.4f} | {r['macro_f']:>9.4f} | {r['bin_f1']:>10.4f}")
    lines += [
        "-" * len(header),
        f"{'Mean':>5} | {mean_acc:>9.4f} | {'':>8} | {'':>8} | {mean_mf1:>9.4f} | {mean_bf1:>10.4f}",
        f"{'Std':>5} | {std_acc:>9.4f} | {'':>8} | {'':>8} | {std_mf1:>9.4f} |",
    ]
    (out_dir / "kfold_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"[kfold] Summary saved → {out_dir / 'kfold_summary.txt'}")

    # ── Chart 1: accuracy per fold bar chart ──────────────────────────────────
    fold_ids = [r["fold"] for r in fold_results]
    accs     = [r["acc"]  for r in fold_results]
    mf1s     = [r["macro_f"] for r in fold_results]

    fig, ax = plt.subplots(figsize=(max(7, k * 1.2), 4))
    x = np.arange(k)
    w = 0.35
    bars1 = ax.bar(x - w/2, accs, w, label="Accuracy",  color="#4C72B0", alpha=0.85)
    bars2 = ax.bar(x + w/2, mf1s, w, label="Macro-F1",  color="#55A868", alpha=0.85)
    for b in [bars1, bars2]:
        for bar in b:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.005,
                    f"{h:.3f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(mean_acc, color="#4C72B0", linestyle="--", linewidth=1,
               label=f"Mean Acc={mean_acc:.3f}")
    ax.axhline(mean_mf1, color="#55A868", linestyle="--", linewidth=1,
               label=f"Mean F1={mean_mf1:.3f}")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Fold {i}" for i in fold_ids])
    ax.set_ylim(max(0, min(accs + mf1s) - 0.1), 1.05)
    ax.set_ylabel("Score")
    ax.set_title(f"{k}-Fold CV — Accuracy & Macro-F1 per Fold", fontsize=12)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.4)
    fig.tight_layout()
    p1 = out_dir / "kfold_fold_acc.png"
    fig.savefig(str(p1), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[kfold] Fold accuracy chart → {p1}")

    # ── Chart 2: per-class F1 across folds (mean ± std) ───────────────────────
    class_f1_mean = []
    class_f1_std  = []
    for rk in RISK_KEYS:
        vals = [r["per_class_f1"].get(rk, 0.0) for r in fold_results]
        class_f1_mean.append(np.mean(vals))
        class_f1_std.append(np.std(vals))

    short_bar = [SHORT_NAMES.get(c, c).replace("\n", " ") for c in RISK_KEYS]
    x2 = np.arange(len(RISK_KEYS))

    fig2, ax2 = plt.subplots(figsize=(max(12, len(RISK_KEYS) * 1.4), 5))
    ax2.bar(x2, class_f1_mean, 0.6, yerr=class_f1_std, capsize=4,
            color="#4C72B0", alpha=0.85, label="Mean F1 (±std)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(short_bar, fontsize=9, rotation=30, ha="right")
    ax2.set_ylim(0, 1.15)
    ax2.set_ylabel("F1-score")
    ax2.set_title(f"{k}-Fold CV — Per-Class F1 (Mean ± Std)", fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.4)
    for i, (m, s) in enumerate(zip(class_f1_mean, class_f1_std)):
        ax2.text(i, m + s + 0.02, f"{m:.2f}", ha="center", va="bottom", fontsize=7.5)
    fig2.tight_layout()
    p2 = out_dir / "kfold_per_class.png"
    fig2.savefig(str(p2), dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"[kfold] Per-class F1 chart  → {p2}")

    # ── Chart 3: K-fold boxplot ───────────────────────────────────────────────
    box_data = {
        "Accuracy":  accs,
        "Macro-F1":  mf1s,
        "Binary-F1": [r["bin_f1"] for r in fold_results],
    }
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    fig3.patch.set_facecolor("#F0F0FA")
    ax3.set_facecolor("#F8F8FF")

    bp = ax3.boxplot(
        box_data.values(),
        labels=box_data.keys(),
        patch_artist=True,
        widths=0.5,
        medianprops=dict(color="#333", linewidth=2),
        whiskerprops=dict(color="#666"),
        capprops=dict(color="#666"),
    )
    colors_box = ["#4C72B0", "#55A868", "#DD8452"]
    for patch, color in zip(bp["boxes"], colors_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    for i, (label, vals) in enumerate(box_data.items(), start=1):
        ax3.scatter([i] * len(vals), vals, color="#333", s=30, zorder=5, alpha=0.7)
        m = np.mean(vals)
        s = np.std(vals)
        ax3.text(i, max(vals) + 0.015, f"μ={m:.3f}\nσ={s:.3f}",
                 ha="center", va="bottom", fontsize=8, color="#333")

    ax3.set_ylim(max(0, min(accs + mf1s) - 0.15), 1.08)
    ax3.set_ylabel("Score", fontsize=11)
    ax3.set_title(f"{k}-Fold Cross-Validation — Score Distribution",
                  fontsize=12, fontweight="bold", pad=14)
    ax3.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax3.set_axisbelow(True)
    fig3.tight_layout()
    p3 = out_dir / "kfold_boxplot.png"
    fig3.savefig(str(p3), dpi=150, bbox_inches="tight")
    plt.close(fig3)
    print(f"[kfold] Boxplot chart       → {p3}")

    return fold_results


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train BERT clause risk classifier (Plan B)")
    parser.add_argument("--model_name",      default="bert-base-uncased",
                        help="Base model (HuggingFace name or local path)")
    parser.add_argument("--squad_data",      default="backend/data/employment_train.json")
    parser.add_argument("--cuad_data",       default="backend/data/cuad_classified.jsonl",
                        help="CUAD-sourced classification samples (~800)")
    parser.add_argument("--synthetic_data",  default="backend/data/cuad_synthetic_employment_risks.jsonl")
    parser.add_argument("--additional_data", default="backend/data/cuad_additional_english_training.jsonl")
    parser.add_argument("--output_dir",      default="backend/models/clause_classifier")
    parser.add_argument("--eval_dir",        default="backend/evaluation")
    parser.add_argument("--split_output",    default="backend/data/classifier_split.json",
                        help="Persisted train/eval split keys for leakage-free reproducible evaluation.")
    parser.add_argument("--epochs",          type=int,   default=4)
    parser.add_argument("--batch_size",      type=int,   default=8)
    parser.add_argument("--learning_rate",   type=float, default=3e-5)
    parser.add_argument("--max_length",      type=int,   default=512)
    parser.add_argument("--warmup_ratio",    type=float, default=0.1)
    parser.add_argument("--max_cuad_samples", type=int, default=0,
                        help="Max samples from cuad_classified.jsonl (0 = use all)")
    parser.add_argument("--eval_split",      type=float, default=0.2,
                        help="Fraction held out for evaluation after training (0 = skip eval).")
    parser.add_argument("--kfold",           type=int,   default=5,
                        help="Number of folds for cross-validation (0 = skip kfold).")
    args = parser.parse_args()

    from datasets import Dataset
    from sklearn.model_selection import train_test_split
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    label2id = {k: i for i, k in enumerate(RISK_KEYS)}
    id2label = {i: k for k, i in label2id.items()}

    # ── Load all data ──────────────────────────────────────────────────────────
    all_samples = []

    import random as _rng
    _rng.seed(42)

    for path_str, loader, tag in [
        (args.squad_data,      load_squad_as_classification, "SQuAD"),
        (args.cuad_data,       load_jsonl,                   "CUAD"),
        (args.synthetic_data,  load_jsonl,                   "Synthetic-4"),
        (args.additional_data, load_jsonl,                   "Additional"),
    ]:
        if not path_str:
            continue
        p = Path(path_str)
        if p.exists():
            s = loader(p)
            if tag == "CUAD" and args.max_cuad_samples > 0 and len(s) > args.max_cuad_samples:
                s = _rng.sample(s, args.max_cuad_samples)
                print(f"[data] {tag:12s}: sampled {len(s):4d} from {loader.__name__}")
            else:
                print(f"[data] {tag:12s}: {len(s):4d} samples")
            all_samples.extend(s)
        else:
            print(f"[warn] Not found: {path_str}")

    if not all_samples:
        raise ValueError("No training data found.")

    raw_dist = Counter(s["label"] for s in all_samples)
    print(f"[data] Raw total: {len(all_samples)} | Distribution: {dict(raw_dist)}")
    all_samples, dropped = _deduplicate_samples(all_samples)
    dedup_dist = Counter(s["label"] for s in all_samples)
    print(f"[data] Dedup total: {len(all_samples)} | Dropped duplicates/empty: {dropped}")
    print(f"[data] Dedup distribution: {dict(dedup_dist)}\n")

    # ── Train / eval split ─────────────────────────────────────────────────────
    if args.eval_split > 0:
        train_samples, eval_samples = train_test_split(
            all_samples,
            test_size=args.eval_split,
            random_state=42,
            stratify=[s["label"] for s in all_samples],
        )
        print(f"[data] Train: {len(train_samples)}  |  Eval: {len(eval_samples)}")
    else:
        train_samples = all_samples
        eval_samples  = []
        print(f"[data] Train: {len(train_samples)}  |  Eval: skipped")

    # Persist split so evaluate_classifier.py can reuse the exact same holdout.
    split_out = Path(args.split_output)
    split_out.parent.mkdir(parents=True, exist_ok=True)
    split_payload = {
        "version": 1,
        "random_state": 42,
        "eval_split": args.eval_split,
        "deduped_total": len(all_samples),
        "train_size": len(train_samples),
        "eval_size": len(eval_samples),
        "train_keys": [_sample_key(s) for s in train_samples],
        "eval_keys": [_sample_key(s) for s in eval_samples],
    }
    split_out.write_text(json.dumps(split_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[data] Saved split file → {split_out}")

    # ── K-Fold cross-validation on TRAIN partition only ────────────────────────
    if args.kfold >= 2:
        run_kfold(
            all_samples=train_samples,
            label2id=label2id,
            id2label=id2label,
            args=args,
            out_dir=Path(args.eval_dir),
        )
    else:
        print("[kfold] Skipped (--kfold < 2)")

    # ── Tokenize ───────────────────────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)

    train_dataset = Dataset.from_dict({
        "text":   [s["text"]  for s in train_samples],
        "labels": [label2id[s["label"]] for s in train_samples],
    })

    def tokenize_batch(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_length,
        )

    train_dataset = train_dataset.map(tokenize_batch, batched=True, remove_columns=["text"])

    # ── Model ──────────────────────────────────────────────────────────────────
    from transformers import DataCollatorWithPadding
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(RISK_KEYS),
        id2label=id2label,
        label2id=label2id,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        weight_decay=0.01,
        logging_steps=10,
        save_steps=500,
        save_total_limit=2,
        fp16=False,
        no_cuda=True,
        report_to=[],
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    print(f"[train] Epochs={args.epochs}  batch={args.batch_size}  lr={args.learning_rate}\n")
    trainer.train()

    # ── Save model ─────────────────────────────────────────────────────────────
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    with open(output_dir / "label2id.json", "w", encoding="utf-8") as f:
        json.dump(label2id, f, indent=2)
    with open(output_dir / "id2label.json", "w", encoding="utf-8") as f:
        json.dump(id2label, f, indent=2)

    print(f"\n[done] Model saved → {output_dir}")

    # ── Post-training evaluation ───────────────────────────────────────────────
    if eval_samples:
        print("\n[eval] Running post-training evaluation …")
        run_evaluation(
            model=model,
            tokenizer=tokenizer,
            test_samples=eval_samples,
            label2id=label2id,
            id2label=id2label,
            out_dir=Path(args.eval_dir),
            max_length=args.max_length,
            train_samples=train_samples,
        )


if __name__ == "__main__":
    main()
