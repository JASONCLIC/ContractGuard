"""
Build a classification dataset from real CUAD data combined with existing synthetic data.

Two data sources:
  A. CUAD_v1.json  (SQuAD-format annotations, 41 clause types, ~510 contracts)
     - Downloaded from Zenodo: https://zenodo.org/record/4599830/files/CUAD_v1.json
     - OR auto-downloaded by this script
  B. theatticusproject/cuad  (HuggingFace, raw PDFs, 511 contracts)
     - Text extracted via pdfplumber; keyword-labelled (lower quality, optional)

Pipeline:
  CUAD_v1.json ──► map 41 CUAD categories ──► our 10 risk_keys ──► jsonl
  HF PDFs      ──► pdfplumber text ──────────► keyword label ──────► jsonl (optional)
  Existing synthetic data ──────────────────────────────────────────► jsonl

Output:
  backend/data/cuad_classified.jsonl   (all CUAD-sourced samples, classified)

Usage:
  # Auto-download CUAD_v1.json + combine with existing data:
  python backend/scripts/build_cuad_dataset.py

  # Use local CUAD_v1.json file:
  python backend/scripts/build_cuad_dataset.py --cuad_json /path/to/CUAD_v1.json

  # Also extract from HuggingFace PDFs:
  python backend/scripts/build_cuad_dataset.py --use_hf_pdfs
"""

import argparse
import json
import random
import re
import ssl
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

# ── Load label mapping from JSON ──────────────────────────────────────────────
# Source: backend/data/cuad_synthetic_label_map.json
# Contains CUAD 41 category → 10+1 risk_key mapping

_LABEL_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "cuad_synthetic_label_map.json"

def _load_label_map():
    with open(_LABEL_MAP_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload["cuad_category_to_risk_key"], payload["risk_keys"]

CUAD_CATEGORY_TO_RISK_KEY, RISK_KEYS = _load_label_map()


def _norm_category(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").strip().lower()).strip()


CUAD_CATEGORY_TO_RISK_KEY_NORM = {
    _norm_category(k): v for k, v in CUAD_CATEGORY_TO_RISK_KEY.items()
}

CUAD_V1_URLS = [
    # Legacy Zenodo URL (may 404 depending on mirror state).
    "https://zenodo.org/record/4599830/files/CUAD_v1.json",
    # Direct HuggingFace dataset file (stable fallback).
    "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/CUAD_v1/CUAD_v1.json?download=true",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_cuad_category(question: str) -> str:
    """
    CUAD questions look like:
      "Highlight ... related to 'Non-Compete' that should be reviewed ..."
    Extract the quoted category name.
    """
    m = re.search(r'"([^"]+)"', question) or re.search(r"'([^']+)'", question)
    return m.group(1) if m else ""


def download_cuad_v1(dest: Path) -> bool:
    if dest.exists():
        print(f"[cuad] CUAD_v1.json already exists at {dest}")
        return True
    print(f"[cuad] Downloading CUAD_v1.json (~13 MB)…")

    # Use certifi CA bundle first to avoid SSL cert issues on some machines/VMs.
    ssl_ctx = None
    try:
        import certifi  # type: ignore
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ssl_ctx = None

    last_err = None
    for url in CUAD_V1_URLS:
        try:
            print(f"[cuad] Trying source: {url}")
            if ssl_ctx is not None:
                with urllib.request.urlopen(url, context=ssl_ctx) as resp:
                    dest.write_bytes(resp.read())
            else:
                urllib.request.urlretrieve(url, str(dest))
            print(f"[cuad] Saved to {dest}")
            return True
        except Exception as e:
            last_err = e
            print(f"[cuad] Source failed: {e}")

    print(f"[cuad] Download failed after all sources: {last_err}")
    return False


def parse_cuad_v1(path: Path, max_negatives_per_category: int = 200):
    """
    Parse CUAD_v1.json (SQuAD v2 format) into classification samples.

    For each (context, question) pair:
      - answers non-empty  → positive for mapped risk_key
      - answers empty      → no_risk  (sampled to control class balance)

    Returns list of {"text": ..., "label": ..., "risk_key": ..., "source": "cuad"}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    positives = []
    negatives_bucket: dict = defaultdict(list)  # category → list of contexts

    for article in data.get("data", []):
        for para in article.get("paragraphs", []):
            context = para.get("context", "").strip()
            if not context:
                continue
            for qa in para.get("qas", []):
                question = qa.get("question", "")
                answers = qa.get("answers", {})
                if isinstance(answers, list):
                    answer_texts = [a.get("text", "") for a in answers if isinstance(a, dict)]
                elif isinstance(answers, dict):
                    answer_texts = answers.get("text", [])
                else:
                    answer_texts = []

                category = extract_cuad_category(question)
                risk_key = (
                    CUAD_CATEGORY_TO_RISK_KEY.get(category)
                    or CUAD_CATEGORY_TO_RISK_KEY_NORM.get(_norm_category(category))
                )

                if answer_texts:
                    # Positive example: use the answer span as the text
                    # (the answer span is the actual risky clause text)
                    if not risk_key:
                        # Skip CUAD categories that are outside our mapped risk taxonomy.
                        continue
                    evidence = answer_texts[0].strip()
                    if len(evidence) > 20:
                        label = risk_key
                        positives.append({
                            "text": evidence,
                            "label": label,
                            "risk_key": label,
                            "source": "cuad",
                            "context_snippet": context[:200],
                        })
                else:
                    # Negative example: keep a sample of no_risk contexts
                    if risk_key and len(negatives_bucket[category]) < max_negatives_per_category:
                        negatives_bucket[category].append(context[:512])

    # Convert sampled negatives to no_risk samples
    negatives = []
    for cat, ctxs in negatives_bucket.items():
        sampled = random.sample(ctxs, min(len(ctxs), max_negatives_per_category))
        for ctx in sampled:
            negatives.append({
                "text": ctx,
                "label": "no_risk",
                "risk_key": "no_risk",
                "source": "cuad",
            })

    return positives, negatives


def extract_text_from_hf_pdfs(max_contracts: int = 50):
    """
    Load theatticusproject/cuad from HuggingFace, extract text from PDFs.
    Returns list of (contract_text, title) tuples.
    Requires pdfplumber.
    """
    try:
        import io
        import pdfplumber
        from datasets import load_dataset, VerificationMode
    except ImportError as e:
        print(f"[hf] Skipping PDF extraction: {e}")
        return []

    print(f"[hf] Loading theatticusproject/cuad (PDFs)…")
    ds = load_dataset(
        "theatticusproject/cuad",
        verification_mode=VerificationMode.NO_CHECKS,
    )
    train = ds["train"]

    # Access raw bytes without triggering the Pdf decoder
    raw = train._data.to_pydict()
    pdf_entries = raw.get("pdf", [])[:max_contracts]

    results = []
    for i, entry in enumerate(pdf_entries):
        try:
            if isinstance(entry, dict):
                pdf_bytes = entry.get("bytes") or entry.get("path")
                if pdf_bytes is None:
                    continue
                if isinstance(pdf_bytes, str):
                    with open(pdf_bytes, "rb") as f:
                        pdf_bytes = f.read()
            else:
                pdf_bytes = bytes(entry)

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages[:20]]
            full_text = "\n".join(pages_text).strip()
            if len(full_text) > 200:
                results.append(full_text)
            if (i + 1) % 10 == 0:
                print(f"[hf] Extracted {i + 1}/{len(pdf_entries)} contracts")
        except Exception as e:
            print(f"[hf] Failed to extract contract {i}: {e}")

    print(f"[hf] Extracted text from {len(results)} contracts")
    return results


def keyword_label_text(text: str) -> list:
    """
    Auto-label a contract text chunk with risk_keys using keyword matching.
    Returns list of (snippet, risk_key) pairs.
    Used for PDF-sourced text that has no QA annotations.
    """
    KEYWORD_MAP = {
        "non_compete":            ["non-compete", "non compete", "shall not compete",
                                   "prohibited from engaging", "no-solicit", "garden leave"],
        "ip_ownership_assignment":["work for hire", "work made for hire", "intellectual property",
                                   "assigns all right", "ip ownership", "all inventions"],
        "excessive_penalty":      ["liquidated damages", "penalty equal to", "shall repay",
                                   "penalty of", "clawback", "performance bond"],
        "unilateral_exemption":   ["cap on liability", "limitation of liability",
                                   "shall not be liable", "no liability", "disclaims all"],
        "vague_termination":      ["termination for convenience", "terminate without cause",
                                   "terminate at will", "sole discretion"],
        "confidentiality":        ["non-disparagement", "shall not disclose", "confidential",
                                   "non-disclosure", "trade secret"],
        "dispute_resolution":     ["governing law", "jurisdiction", "arbitration",
                                   "dispute resolution", "binding arbitration"],
    }

    # Split contract into sentence-level chunks (~300 chars)
    sentences = re.split(r"(?<=[.;])\s+", text)
    chunks = []
    buf = ""
    for s in sentences:
        buf += " " + s
        if len(buf) > 200:
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())

    labelled = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        for risk_key, kws in KEYWORD_MAP.items():
            if any(kw in chunk_lower for kw in kws):
                labelled.append({
                    "text": chunk[:500],
                    "label": risk_key,
                    "risk_key": risk_key,
                    "source": "cuad_pdf_keyword",
                })
                break  # one label per chunk
    return labelled


def load_existing_jsonl(path: Path):
    samples = []
    if not path.exists():
        return samples
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                rk = obj.get("risk_key", obj.get("label", "no_risk"))
                if rk not in RISK_KEYS:
                    rk = "no_risk"
                samples.append({"text": obj["text"], "label": rk, "risk_key": rk,
                                 "source": obj.get("source", "synthetic")})
    return samples


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build CUAD classification dataset")
    parser.add_argument("--cuad_json",  default="backend/data/CUAD_v1.json",
                        help="Path to CUAD_v1.json (auto-downloaded if missing)")
    parser.add_argument("--out",        default="backend/data/cuad_classified.jsonl")
    parser.add_argument("--synthetic1", default="backend/data/cuad_synthetic_employment_risks.jsonl")
    parser.add_argument("--synthetic2", default="backend/data/cuad_additional_english_training.jsonl")
    parser.add_argument("--use_hf_pdfs", action="store_true",
                        help="Also extract text from HuggingFace PDF dataset (slow)")
    parser.add_argument("--max_pdf_contracts", type=int, default=50)
    parser.add_argument("--max_neg_per_cat",   type=int, default=200,
                        help="Max no_risk samples per CUAD category")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    all_samples = []

    # ── A. CUAD_v1.json ────────────────────────────────────────────────────────
    cuad_path = Path(args.cuad_json)
    if download_cuad_v1(cuad_path):
        pos, neg = parse_cuad_v1(cuad_path, max_negatives_per_category=args.max_neg_per_cat)
        all_samples.extend(pos)
        all_samples.extend(neg)
        print(f"[cuad] Parsed: {len(pos)} positives + {len(neg)} negatives from CUAD_v1.json")

        pos_dist = Counter(s["risk_key"] for s in pos)
        print(f"[cuad] Positive distribution: {dict(pos_dist)}")
    else:
        print("[cuad] CUAD_v1.json not available. "
              f"Download manually to {cuad_path} from one of: {CUAD_V1_URLS}")

    # ── B. HuggingFace PDFs (optional) ────────────────────────────────────────
    if args.use_hf_pdfs:
        pdf_texts = extract_text_from_hf_pdfs(max_contracts=args.max_pdf_contracts)
        pdf_samples = []
        for text in pdf_texts:
            pdf_samples.extend(keyword_label_text(text))
        all_samples.extend(pdf_samples)
        print(f"[hf]  PDF-sourced keyword-labelled: {len(pdf_samples)} samples")

    # ── C. Existing synthetic data ─────────────────────────────────────────────
    for synth_path_str in [args.synthetic1, args.synthetic2]:
        synth_samples = load_existing_jsonl(Path(synth_path_str))
        all_samples.extend(synth_samples)
        print(f"[syn] Loaded {len(synth_samples):4d} samples ← {Path(synth_path_str).name}")

    if not all_samples:
        raise ValueError("No data produced. Check paths and network access.")

    # ── Save ───────────────────────────────────────────────────────────────────
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    random.shuffle(all_samples)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps({"text": s["text"], "label": s["label"],
                                 "risk_key": s["risk_key"], "source": s["source"]},
                               ensure_ascii=False) + "\n")

    dist = Counter(s["risk_key"] for s in all_samples)
    print(f"\n[done] Saved {len(all_samples)} samples → {out_path}")
    print(f"[done] Label distribution: {dict(dist)}")
    print(f"\nNext step: retrain with --additional_data {out_path}")
    print(f"  python backend/scripts/train_cuad_classifier.py \\")
    print(f"    --additional_data {out_path} --epochs 4 --eval_split 0.15")


if __name__ == "__main__":
    main()
