from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class DesensitizeResult:
    redacted_text: str
    redaction_summary: List[Dict[str, Union[int, str]]]
    total_redactions: int


_ENTITY_FIELD_PLACEHOLDERS = {
    "party_a": "[EMPLOYER]",
    "party_b": "[EMPLOYEE]",
    "work_location": "[WORK LOCATION]",
    "salary_amount": "[SALARY]",
}

_REGEX_PATTERNS = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (
        "PHONE",
        re.compile(
            r"(?:\+?\d{1,3}[\s\-\.]?)?(?:\(?\d{2,4}\)?[\s\-\.]?)\d{3,4}[\s\-\.]?\d{3,4}\b"
        ),
        "[PHONE]",
    ),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    ("NIN", re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"), "[NIN]"),
    ("PASSPORT", re.compile(r"\bPassport(?:\s*No\.?)?[:\s]*[A-Z0-9]{6,9}\b", re.IGNORECASE), "[PASSPORT]"),
    (
        "DATE OF BIRTH",
        re.compile(
            r"\b(?:date\s+of\s+birth|dob)\s*[:\-]?\s*(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|"
            r"\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}|"
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
            re.IGNORECASE,
        ),
        "[DATE OF BIRTH]",
    ),
    (
        "BANK ACCOUNT",
        re.compile(r"\b(?:[A-Z]{2}\d{2}[A-Z0-9]{10,30}|\d{8,20})\b"),
        "[BANK ACCOUNT]",
    ),
]

_ADDRESS_PATTERN = re.compile(
    r"\b(?:address|residing\s+at|located\s+at)\s*[:\-]?\s*([^\n,;]{8,120})",
    re.IGNORECASE,
)


def _safe_entity_values(key_info: Optional[Dict]) -> List[Tuple[str, str]]:
    if not key_info:
        return []
    pairs: List[Tuple[str, str]] = []
    for field, placeholder in _ENTITY_FIELD_PLACEHOLDERS.items():
        value = (key_info.get(field) or "").strip()
        if not value or value.lower() == "not identified":
            continue
        pairs.append((value, placeholder))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def _replace_literal(text: str, literal: str, replacement: str) -> Tuple[str, int]:
    if not literal:
        return text, 0
    pattern = re.compile(r"\b" + re.escape(literal) + r"\b", re.IGNORECASE)
    return pattern.subn(replacement, text)


def desensitize_text(text: str, key_info: Optional[Dict] = None) -> DesensitizeResult:
    masked = text or ""
    counts: Dict[str, int] = {}

    for entity_value, placeholder in _safe_entity_values(key_info):
        masked, n = _replace_literal(masked, entity_value, placeholder)
        if n > 0:
            counts[placeholder.strip("[]")] = counts.get(placeholder.strip("[]"), 0) + n

    for label, pattern, replacement in _REGEX_PATTERNS:
        masked, n = pattern.subn(replacement, masked)
        if n > 0:
            counts[label] = counts.get(label, 0) + n

    has_work_location = bool((key_info or {}).get("work_location"))
    if not has_work_location:
        masked, n = _ADDRESS_PATTERN.subn("[ADDRESS]", masked)
        if n > 0:
            counts["ADDRESS"] = counts.get("ADDRESS", 0) + n

    summary = [{"type": t, "count": c} for t, c in counts.items() if c > 0]
    summary.sort(key=lambda item: int(item["count"]), reverse=True)
    total = sum(int(item["count"]) for item in summary)
    return DesensitizeResult(
        redacted_text=masked,
        redaction_summary=summary,
        total_redactions=total,
    )
