from __future__ import annotations

import re

from .bert_clause_classifier import BertClauseClassifier
from .ner_qa_extractor import extract_key_info_qa
from ..services.llm_explainer import explain_risks_batch
from ..services.desensitizer import desensitize_text

# 匹配条款标题（中英文双语）
# 中文：第X条 / （一） / 一、
# 英文：Article 1 / Section 1 / Clause 1 / 1. / (1)
CLAUSE_HEADING_RE = re.compile(
    r"^("
    r"(?:Article|Section|Clause|ARTICLE|SECTION|CLAUSE)\s+\d+"  # Article 1 / Section 2
    r"|第[零一二三四五六七八九十百千\d]+条"                      # 第一条 / 第1条
    r"|[（(][一二三四五六七八九十\d]+[）)]"                       # （一）/ (1)
    r"|(?<![0-9])[1-9][0-9]{0,1}[.、．](?!\d)"                  # 1. / 2、
    r"|[一二三四五六七八九十]+[、．.]"                            # 一、 二、
    r")",
    re.IGNORECASE,
)


_HEADING_INLINE_RE = re.compile(
    r"((?:Article|Section|Clause)\s+\d+"
    r"|第[零一二三四五六七八九十百千\d]+条"
    r"|[（(][一二三四五六七八九十\d]+[）)]"
    r"|(?<![0-9])[1-9][0-9]{0,1}[.、．](?!\d)"
    r"|[一二三四五六七八九十]+[、．.])",
    re.IGNORECASE,
)

# 条款标题后紧跟的短标题（中英文均适用，最多 30 个字符）
_TITLE_SUFFIX_RE = re.compile(r"^[\s　]*([^\n，。；：:（(\r]{1,30})")


def _extract_heading_and_body(chunk: str) -> tuple[str, str]:
    """
    从 chunk 的开头提取"第X条 标题名"作为 heading，剩余为 body。
    例: "第一条 合同期限 合同期限为2年..." -> ("第一条 合同期限", "合同期限为2年...")
    """
    m = _HEADING_INLINE_RE.match(chunk)
    if not m:
        return chunk[:20], chunk
    base = m.group(0)            # 如 "第一条"
    rest = chunk[m.end():]       # 空格 + 短标题 + 正文
    suffix = _TITLE_SUFFIX_RE.match(rest)
    if suffix:
        heading = f"{base} {suffix.group(1).strip()}"
        body = rest[suffix.end():].strip()
    else:
        heading = base
        body = rest.strip()
    # 保留完整内容（含heading）以便 NLP 分析
    return heading, chunk


def _split_by_heading(text: str):
    """
    在全文中扫描所有条款标题位置（不依赖换行），按边界切分。
    """
    matches = list(_HEADING_INLINE_RE.finditer(text))
    if not matches:
        return []

    clauses = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            heading, content = _extract_heading_and_body(chunk)
            clauses.append({"heading": heading, "content": content})
    return clauses


def _segment_clauses(contract_text: str):
    # 先用逐行匹配（适用于格式良好的文本）
    lines = [line.strip() for line in contract_text.splitlines() if line.strip()]
    clauses = []
    current = None

    for line in lines:
        if CLAUSE_HEADING_RE.match(line):
            if current:
                clauses.append(current)
            heading, content = _extract_heading_and_body(line)
            current = {"heading": heading, "content": content}
        else:
            if not current:
                current = {"heading": "Preamble", "content": line}
            else:
                current["content"] += f"\n{line}"

    if current:
        clauses.append(current)

    # Fallback 1: 全文内联扫描（处理 PDF 丢失换行的情况）
    if len(clauses) <= 1:
        clauses = _split_by_heading(contract_text)

    # Fallback 2: 按标点切分（中英文标点均覆盖）
    if len(clauses) <= 1 and lines:
        pieces = re.split(r"[；;。\.]\s{2,}", "".join(lines))
        pieces = [p.strip() for p in pieces if len(p.strip()) > 10]
        if len(pieces) > 1:
            clauses = [{"heading": f"Clause {i + 1}", "content": p} for i, p in enumerate(pieces)]

    normalized = []
    for idx, clause in enumerate(clauses, start=1):
        normalized.append(
            {
                "index_num": idx,
                "heading": clause.get("heading") or f"Clause {idx}",
                "content": clause["content"],
            }
        )
    return normalized


def run_pipeline(contract_text: str, contract_type: str = "labor", progress_callback=None):
    if progress_callback:
        progress_callback(15, "Segmenting contract clauses")
    clauses = _segment_clauses(contract_text)
    if progress_callback:
        progress_callback(35, "Identifying risks by clause")
    detector = BertClauseClassifier()
    # detect() mutates clauses with unified labels (risk_key/category/confidence)
    risks, missing_items = detector.detect(clauses, contract_text, contract_type=contract_type)
    if progress_callback:
        progress_callback(55, "Extracting key information")
    key_info = extract_key_info_qa(contract_text, clauses=clauses)
    if progress_callback:
        progress_callback(70, "Redacting sensitive information")
    redact_result = desensitize_text(contract_text, key_info=key_info)
    if progress_callback:
        progress_callback(75, "Generating risk explanations")
    risks = explain_risks_batch(
        risks,
        clauses,
        progress_callback=progress_callback,
        progress_start=75,
        progress_end=90,
    )
    if progress_callback:
        progress_callback(95, "Finalizing analysis result")

    return {
        "clauses": clauses,
        "key_info": key_info,
        "risks": risks,
        "missing_items": missing_items,
        "desensitized_text": redact_result.redacted_text,
        "redaction_summary": redact_result.redaction_summary,
        "total_redactions": redact_result.total_redactions,
    }
