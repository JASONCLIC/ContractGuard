import re
from typing import Optional


def _pick(pattern: str, text: str, group_index=1, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags=flags)
    return m.group(group_index).strip() if m else None


def extract_key_info(text: str):
    return {
        "contract_name":          _contract_name(text),
        "party_a":                _party_a(text),
        "party_b":                _party_b(text),
        "salary_amount":          _salary_amount(text),
        "payment_cycle":          _payment_cycle(text),
        "job_title":              _job_title(text),
        "work_location":          _work_location(text),
        "probation":              _probation(text),
        "contract_term":          _contract_term(text),
        "termination_conditions": _termination(text),
        "breach_liability":       _breach(text),
        "dispute_resolution":     _dispute(text),
    }


# ── helpers ──────────────────────────────────────────────────────────────────

def _contract_name(text):
    # English: Employment Contract / Internship Agreement / Service Contract
    en = _pick(
        r"(employment\s+contract|internship\s+agreement|service\s+contract"
        r"|labour\s+contract|labor\s+contract|work\s+agreement)",
        text,
    )
    if en:
        return en.title()
    # Chinese fallback
    return _pick(r"(劳动合同|实习协议|劳务合同)", text) or "Not identified"


def _party_a(text):
    return (
        _pick(r"(?:Employer|Company|Party\s*A|Employer['']?s?\s+Name)\s*[:：]\s*([^\n,，。]+)", text)
        or _pick(r"甲方[:：]\s*([^\n，,。]+)", text)
        or "Not identified"
    )


def _party_b(text):
    return (
        _pick(r"(?:Employee|Worker|Intern|Party\s*B|Employee['']?s?\s+Name)\s*[:：]\s*([^\n,，。]+)", text)
        or _pick(r"乙方[:：]\s*([^\n，,。]+)", text)
        or "Not identified"
    )


def _salary_amount(text):
    # Require explicit currency prefix to avoid matching percentages like "80% of salary"
    en = _pick(
        r"(?:salary|wage|stipend|allowance|compensation|remuneration|pay)[^\d$£¥€]{0,50}"
        r"((?:RMB|USD|GBP|€|£|\$|¥|CNY)\s*[\d,\.]+(?:\s*(?:per\s+(?:month|year|annum|week)|monthly|annually))?)",
        text,
    )
    if en:
        return en
    # Chinese fallback
    return (
        _pick(r"(?:工资|薪资|补贴|津贴)[^\d]*(\d+(?:\.\d+)?(?:元|万)?(?:/月)?)", text)
        or "Not identified"
    )


def _payment_cycle(text):
    en = _pick(
        r"(monthly|bi[-\s]?weekly|weekly|fortnightly"
        r"|paid\s+on\s+the\s+\w+\s+(?:day|of\s+each\s+month)"
        r"|every\s+(?:month|week|two\s+weeks))",
        text,
    )
    if en:
        return en
    return (
        _pick(r"(按月|按周|按季度|每月[^\n，,。]*)", text)
        or "Not identified"
    )


def _job_title(text):
    # Strip the document after the signature block to avoid matching form fields
    sig_m = re.search(r"\bIN\s+WITNESS\s+WHEREOF\b|For\s+the\s+Company\s*:\s*Name", text, re.IGNORECASE)
    body = text[:sig_m.start()] if sig_m else text

    return (
        # Explicit label with colon, answer must start with a letter (not a blank "_____")
        _pick(r"(?:position|job\s+title|role)\s*[:：]\s*([A-Za-z][^\n,，。]+)", body)
        # "title: X" only when followed by a real value
        or _pick(r"\btitle\s*[:：]\s*([A-Za-z][A-Za-z\s\-\/&,\.]+)", body)
        # Natural language: "employed in the position of Senior Analyst"
        or _pick(r"employed\s+(?:in\s+the\s+)?(?:position|role)\s+of\s+([A-Z][^\n.,]+)", body)
        # Natural language: "hired / appointed as Senior Analyst"
        or _pick(r"(?:hired|appointed|designated)\s+(?:as|to\s+serve\s+as)\s+(?:a\s+|an\s+)?([A-Z][^\n.,]+)", body)
        # Internship: "shall serve as a Business Operations Intern"
        # Lazy match stops before " and …" / " to …" / "," to avoid capturing the next clause
        or _pick(r"(?:shall\s+)?(?:serve|work)\s+as\s+(?:a\s+|an\s+)?([A-Z][^\n.,]+?)(?=\s+and\s|\s+to\s|\s+who\s|,|\.|$)", body)
        or _pick(r"(?:岗位|职位)[:：]?\s*([^\n，,。]+)", body)
        or "Not identified"
    )


def _work_location(text):
    return (
        # Explicit label with colon: "Work Location: London"
        _pick(r"(?:work\s+location|place\s+of\s+work|office\s+location|work(?:ing)?\s+address)\s*[:：]\s*([^\n,，。]+)", text)
        # Natural language: "work location shall be / is the office at ..."
        or _pick(r"work\s+location\s+shall\s+be\s+(?:the\s+)?(?:[^\n]*?(?:office\s+at|located\s+at|based\s+at)\s+)?([A-Z0-9][^\n.]+)", text)
        or _pick(r"(?:place\s+of\s+work|working\s+address)\s+(?:shall\s+be|is)\s+([^\n,，。]+)", text)
        or _pick(r"(?:工作地点|办公地点)[:：]?\s*([^\n，,。]+)", text)
        or "Not identified"
    )


def _probation(text):
    return (
        # Standard: "probationary period is 3 months"
        _pick(r"(?:probation(?:ary)?\s+period|trial\s+period)\s+(?:is|of|shall\s+be)?\s*([^\n,，。]+)", text)
        # Internship: "first two months … assessment period"
        or _pick(
            r"(?:first|initial)\s+((?:\w+\s+){1,3}(?:months?|weeks?))[^\n]{0,60}?"
            r"(?:assessment|evaluation|review|trial)\s+period",
            text,
        )
        # Article-heading style: capture content of probation/assessment article
        or _article_content(text, r"[Pp]robation(?:\s+and\s+[Aa]ssessment)?")
        or _pick(r"试用期[为是]?\s*([^\n，,。]+)", text)
        or "Not identified"
    )


def _article_content(text: str, title_pattern: str, max_chars: int = 300) -> Optional[str]:
    """
    Find the first occurrence of `title_pattern` in `text`, then return
    the content that follows it — stopping before the next Article/Section/Clause
    heading or end-of-string.

    Handles three PDF-output formats:
      1. "Article N  Title  Content…"  — double-space separator
      2. "Article N  Title\\nContent…" — newline separator
      3. "Article N TitleContent…"     — no separator (PDF merge artefact);
         detected via CamelCase boundary e.g. "TerminationThe" → "The…"
    """
    m = re.search(title_pattern, text, re.IGNORECASE)
    if not m:
        return None
    after = text[m.end():]

    # Strategy 1: explicit separator (2+ spaces or newline) within 60 chars
    sep = re.search(r"(?:\s{2,}|\n)\s*([A-Z])", after)
    if sep and sep.start() < 60:
        after = after[sep.start(1):]
    else:
        # Strip leading whitespace / colons / conjunctions (e.g. " and ")
        after = re.sub(r"^[\s:：]+", "", after)
        after = re.sub(r"^(?:and|or|of)\s+", "", after, flags=re.IGNORECASE)
        # Strategy 2: CamelCase smash — capital letter immediately following a
        # lowercase letter within the first 50 chars signals content start.
        # e.g. "PenaltyIf the Intern…" → starts at "If"
        #      "TerminationThe Company…" → starts at "The"
        smash = re.search(r"(?<=[a-z])([A-Z][a-z])", after)
        if smash and smash.start() < 50:
            after = after[smash.start():]

    # Cut before the next article/section heading
    nxt = re.search(r"\b(?:Article|Section|Clause)\s+\d+\b", after)
    if nxt:
        after = after[: nxt.start()]
    return after.replace("\n", " ").strip()[:max_chars] or None


def _contract_term(text):
    v = _article_content(
        text,
        r"(?:contract\s+term|internship\s+term|internship\s+period"
        r"|term\s+of\s+(?:employment|contract|internship)"
        r"|duration\s+of\s+(?:this\s+)?(?:agreement|contract|internship))"
        r"\s*(?:is|shall\s+be)?\s*[:：]?",
    )
    if v:
        return v
    # Inline date range: "internship shall commence on … and continue until …"
    m = re.search(
        r"(?:internship|employment)\s+shall\s+(?:commence|begin|start)\s+on\s+([^\n.]+)",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()[:200]
    m2 = re.search(r"合同期限[为是]?\s*([^\n，,。]+)", text, re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    return "Not identified"


def _termination(text):
    # Full heading: "Termination Conditions / Clause / Provision"
    v = _article_content(
        text, r"[Tt]ermination\s+(?:[Cc]onditions?|[Cc]lause|[Pp]rovision)"
    )
    if v:
        return v
    # Bare heading: "Article N Termination" (internship / simple contracts)
    # Note: no \b at end — heading and content may be joined without space in PDF output
    v2 = _article_content(
        text, r"(?:Article|Section|Clause)\s+\d+\s+[Tt]ermination"
    )
    if v2:
        return v2
    m = re.search(r"(?:解除条件|合同解除)[^\n。]*", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return "Not identified"


def _breach(text):
    # Standard patterns: breach liability, liquidated damages, penalty clause
    v = _article_content(
        text,
        r"(?:[Bb]reach\s+(?:[Ll]iability|[Oo]f\s+[Cc]ontract)"
        r"|[Ll]iquidated\s+[Dd]amages"
        r"|[Pp]enalty\s+[Cc]lause"
        r"|[Bb]reach\s+[Ll]iability\s+and\s+[Pp]enalty)",
    )
    if v:
        return v
    # Internship / non-standard: "Early Departure and Penalty" / "Departure Penalty"
    v2 = _article_content(
        text,
        r"(?:[Ee]arly\s+[Dd]eparture|[Dd]eparture\s+[Pp]enalty"
        r"|[Pp]enalty\s+and\s+[Cc]ompensation"
        r"|[Cc]ompensation\s+and\s+[Pp]enalty)",
    )
    if v2:
        return v2
    m = re.search(r"(?:违约责任|违约金)[^\n。]*", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return "Not identified"


def _dispute(text):
    v = _article_content(
        text,
        r"(?:[Dd]ispute\s+[Rr]esolution"
        r"|[Gg]overning\s+[Ll]aw"
        r"|[Aa]rbitration\s+[Cc]lause)",
    )
    if v:
        return v
    m = re.search(r"争议(?:解决|处理)[^\n。]*", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return "Not identified"
