"""
BERT sequence classifier for employment contract risk detection.
Plan B: classify clause text → risk_key label → build risk item.

Model loading priority:
  1. backend/models/clause_classifier/  (fine-tuned, produced by train_cuad_classifier.py)
  2. Raise RuntimeError

On low-confidence predictions the keyword fallback layer still fires,
so the detector always provides reasonable coverage even without a model.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NO_RISK_LABEL = "no_risk"

_KEYWORD_FALLBACK: Dict[str, List[str]] = {
    "unilateral_exemption": [
        "shall not be liable", "no liability whatsoever",
        "employee assumes all risks", "employer bears no responsibility",
        "all risks shall be borne by", "without any liability",
        "disclaims all liability", "waives any right to assert claims",
    ],
    "excessive_penalty": [
        "liquidated damages", "penalty clause", "penalty equal to",
        "training cost repayment", "clawback",
        "indemnify and hold harmless",
    ],
    "vague_termination": [
        "terminate without cause", "terminate for any reason",
        "at the employer's sole discretion", "unilateral termination",
        "terminate at will", "terminate immediately without notice",
    ],
    "probation_period_risk": [
        "probationary period salary", "probation salary shall",
        "during probation the employer may terminate",
        "probation period may be extended", "confirmation of employment",
    ],
    "wage_payment_unclear": [
        "salary to be decided", "wage to be decided", "remuneration to be confirmed",
        "salary shall be subject to company policy", "compensation as agreed separately",
        "pay at the employer's discretion", "adjusted at the company's sole discretion",
        "salary will be confirmed separately",
    ],
    "overtime_leave_unclear": [
        "working hours may vary", "as required by business needs",
        "hours to be determined by employer",
        "overtime compensation shall be at employer's discretion",
        "employer may adjust working hours without notice",
    ],
    "non_compete": [
        "non-compete", "non compete", "prohibited from working for",
        "garden leave", "shall not engage in any competing",
        "non-competition clause", "restricted from employment",
    ],
    "ip_ownership_assignment": [
        "intellectual property", "work product", "work for hire",
        "assigns to employer", "all inventions", "work made for hire",
        "irrevocably assigns",
    ],
    "confidentiality": [
        "non-disclosure agreement", "nda",
        "shall not disclose any confidential", "strict confidence",
        "proprietary information of the company",
        "confidential information of employer",
        "trade secret",
    ],
    "dispute_resolution": [
        "binding arbitration", "waives any right to a trial by jury",
        "mandatory arbitration", "all disputes shall be resolved by arbitration",
    ],
}

# Keywords that indicate a clause TYPE is PRESENT in the contract.
# Used for missing-clause detection: if none match → clause is missing.
_PRESENCE_KEYWORDS: Dict[str, List[str]] = {
    "missing_dispute_resolution": ["arbitration", "dispute", "mediation", "binding arbitration"],
    "missing_termination_process": ["terminat", "notice period", "dismissal", "resignation"],
    "missing_wage_details": ["salary", "wage", "compensation", "remuneration", "base pay"],
    "missing_work_hours": ["working hours", "overtime", "work schedule", "hours of work"],
    "missing_data_privacy": ["personal data", "privacy", "data protection", "gdpr", "data policy"],
}

# Unified semantic category mapping (kept compatible with frontend category badges).
_RISK_TO_CATEGORY: Dict[str, str] = {
    "wage_payment_unclear": "salary",
    "overtime_leave_unclear": "working_hours",
    "probation_period_risk": "probation",
    "vague_termination": "termination",
    "excessive_penalty": "breach",
    "dispute_resolution": "dispute",
    "non_compete": "general",
    "ip_ownership_assignment": "general",
    "confidentiality": "general",
    "unilateral_exemption": "general",
}


def _fallback_category(text: str) -> str:
    """
    Lightweight fallback for no-risk clauses.
    This keeps clause categories useful for structure view and QA focused extraction.
    """
    t = (text or "").lower()

    if any(k in t for k in ("salary", "wage", "remuneration", "compensation", "pay ", "stipend")):
        return "salary"
    if any(k in t for k in ("work location", "place of work", "office location", "working address")):
        return "work_location"
    if any(k in t for k in ("working hours", "work hours", "overtime", "leave", "vacation", "holiday", "rest day")):
        return "working_hours"
    if any(k in t for k in ("probation", "probationary", "trial period")):
        return "probation"
    if any(k in t for k in ("terminat", "dismiss", "redundan", "layoff", "lay off", "notice period")):
        return "termination"
    if any(k in t for k in ("breach", "liquidated damages", "penalty", "violation")):
        return "breach"
    if any(k in t for k in ("dispute", "arbitration", "governing law", "jurisdiction", "litigation")):
        return "dispute"
    return "general"


class BertClauseClassifier:
    """
    Singleton BERT sequence classifier.

    Call detect(clauses, contract_text) to get (risks, missing_items)
    in the same format as BertRiskDetector.detect().
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        labels_path: Optional[str] = None,
        model_dir: Optional[str] = None,
        confidence_threshold: float = 0.60,
    ):
        if getattr(self, "_initialized", False):
            return

        self._initialized = False
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.tokenizer = None
        self._torch = None

        base_dir = Path(__file__).resolve().parents[2]  # backend/
        self.labels_path = Path(labels_path) if labels_path else base_dir / "data" / "employment_labels.json"
        self._model_dir = Path(model_dir) if model_dir else base_dir / "models" / "clause_classifier"

        self._load_labels()
        self._load_model()
        self._initialized = True

    # ── Label loading ──────────────────────────────────────────────────────────

    def _load_labels(self):
        with open(self.labels_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.risk_types_by_key: Dict = {rt["key"]: rt for rt in payload["risk_types"]}
        self.missing_types_by_key: Dict = {mt["key"]: mt for mt in payload["missing_clause_types"]}

    # ── Model loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _looks_like_model(path: Path) -> bool:
        return path.exists() and (path / "config.json").exists() and (
            (path / "pytorch_model.bin").exists() or (path / "model.safetensors").exists()
        )

    def _load_model(self):
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
        except Exception as exc:
            raise RuntimeError("transformers / torch not installed.") from exc

        self._torch = torch

        if not self._looks_like_model(self._model_dir):
            raise RuntimeError(
                f"Classifier model not found at '{self._model_dir}'. "
                "Train it first: python backend/scripts/train_cuad_classifier.py"
            )

        self.tokenizer = AutoTokenizer.from_pretrained(str(self._model_dir), use_fast=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(str(self._model_dir))
        self.model.eval()
        self.model.to(torch.device("cpu"))

        # id2label is stored in model config by train_cuad_classifier.py
        self.id2label: Dict[int, str] = {int(k): v for k, v in self.model.config.id2label.items()}

    # ── Inference ──────────────────────────────────────────────────────────────

    def _classify(self, text: str) -> Tuple[str, float]:
        """Return (risk_key_or_no_risk, confidence_0_to_1)."""
        import torch

        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits[0]

        probs = torch.softmax(logits, dim=-1)
        best_idx = int(probs.argmax().item())
        confidence = float(probs[best_idx].item())

        raw_label = self.id2label.get(best_idx, NO_RISK_LABEL)
        # Normalise synthetic labels: emp_unilateral_exemption → unilateral_exemption
        risk_key = raw_label.removeprefix("emp_")
        return risk_key, confidence

    # ── Public interface ───────────────────────────────────────────────────────

    def annotate_clauses(self, clauses: List[Dict]) -> None:
        """
        Mutate each clause with unified labels:
          - risk_key
          - risk_confidence
          - category
        """
        for clause in clauses:
            content: str = clause.get("content") or ""
            predicted_key, confidence = self._classify(content)
            clause["risk_key"] = predicted_key
            clause["risk_confidence"] = confidence

            if predicted_key != NO_RISK_LABEL:
                clause["category"] = _RISK_TO_CATEGORY.get(predicted_key, "general")
            else:
                clause["category"] = _fallback_category(content)

    def detect(
        self,
        clauses: List[Dict],
        contract_text: str,
        contract_type: str = "labor",
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Classify every clause.

        Returns:
            risks        – list of risk item dicts
            missing_items – list of missing clause dicts
        """
        risks: List[Dict] = []
        missing_items: List[Dict] = []
        seen: set = set()

        # Unified clause annotation first (single source of truth for category).
        self.annotate_clauses(clauses)

        for clause in clauses:
            content: str = clause.get("content") or ""
            content_lower = content.lower()
            idx = clause["index_num"]
            predicted_key = clause.get("risk_key", NO_RISK_LABEL)
            confidence = float(clause.get("risk_confidence", 0.0))

            # High-confidence model prediction
            model_fired = False
            if (
                predicted_key != NO_RISK_LABEL
                and predicted_key in self.risk_types_by_key
                and confidence >= self.confidence_threshold
            ):
                dedup_key = (idx, predicted_key)
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    rt = self.risk_types_by_key[predicted_key]
                    risks.append(self._make_risk(idx, rt, content))
                model_fired = True

            # Keyword fallback: only used when model predicts no_risk or low confidence.
            # Prevents flooding every clause with risk tags from broad keyword matches.
            if not model_fired:
                for rk, triggers in _KEYWORD_FALLBACK.items():
                    dedup_key = (idx, rk)
                    if dedup_key in seen:
                        continue
                    if any(t.lower() in content_lower for t in triggers):
                        seen.add(dedup_key)
                        rt = self.risk_types_by_key[rk]
                        risks.append(self._make_risk(idx, rt, content))

        # Missing clause detection: document-level keyword presence check
        full_lower = (contract_text or "").lower()
        for missing_key, mt in self.missing_types_by_key.items():
            presence_kws = _PRESENCE_KEYWORDS.get(missing_key, [])
            if not any(kw.lower() in full_lower for kw in presence_kws):
                missing_items.append({
                    "item_name": mt["label"],
                    "description": mt["description"],
                    "potential_risk": mt["risk_explanation"],
                })

        return risks, missing_items

    @staticmethod
    def _make_risk(index_num: int, rt: Dict, content: str) -> Dict:
        return {
            "index_num": index_num,
            "risk_type": rt["label"],
            "risk_level": rt["risk_level"],
            "evidence_sentence": content[:300].strip(),
            "explanation": rt["risk_explanation"],
            "legal_reference": "For reference only. Does not constitute formal legal advice.",
        }
