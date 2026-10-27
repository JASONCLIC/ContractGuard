"""
PDF report generation module — uses reportlab with Helvetica (built-in),
no external fonts required, cross-platform compatible.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONT      = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"

KEY_LABELS: dict[str, str] = {
    "contract_name":          "Contract Type",
    "party_a":                "Employer (Party A)",
    "party_b":                "Employee (Party B)",
    "salary_amount":          "Salary Amount",
    "payment_cycle":          "Payment Cycle",
    "job_title":              "Job Title",
    "work_location":          "Work Location",
    "probation":              "Probation Period",
    "contract_term":          "Contract Term",
    "termination_conditions": "Termination Conditions",
    "breach_liability":       "Breach Liability",
    "dispute_resolution":     "Dispute Resolution",
}

_RISK_LABEL = {"high": "High Risk", "medium": "Medium Risk", "low": "Low Risk"}
_RISK_COLOR = {
    "high":   colors.HexColor("#FF3B30"),
    "medium": colors.HexColor("#FF9500"),
    "low":    colors.HexColor("#007AFF"),
}
_RISK_BG = {
    "high":   colors.HexColor("#FFF0F0"),
    "medium": colors.HexColor("#FFF8F0"),
    "low":    colors.HexColor("#F0F6FF"),
}

# ── 样式定义 ──────────────────────────────────────────────────
def _styles() -> dict:
    blue  = colors.HexColor("#0071E3")
    dark  = colors.HexColor("#1D1D1F")
    gray  = colors.HexColor("#6E6E73")
    lgray = colors.HexColor("#8E8E93")

    return {
        "logo": ParagraphStyle(
            "logo", fontName=_FONT_BOLD, fontSize=18,
            textColor=blue, leading=24, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=_FONT, fontSize=9,
            textColor=gray, leading=14, spaceAfter=3,
        ),
        "meta": ParagraphStyle(
            "meta", fontName=_FONT, fontSize=8,
            textColor=lgray, leading=12, spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "section", fontName=_FONT_BOLD, fontSize=12,
            textColor=dark, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", fontName=_FONT, fontSize=9,
            textColor=dark, leading=14,
        ),
        "small": ParagraphStyle(
            "small", fontName=_FONT, fontSize=8,
            textColor=gray, leading=12,
        ),
        "ok": ParagraphStyle(
            "ok", fontName=_FONT_BOLD, fontSize=10,
            textColor=colors.HexColor("#34C759"),
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", fontName=_FONT, fontSize=7.5,
            textColor=gray, leading=11, spaceBefore=10,
            backColor=colors.HexColor("#F5F5F7"),
            borderPadding=8,
        ),
    }


def _section_header(num: str, title: str, st: dict):
    return Paragraph(f"<font color='#0071E3'>&#9679;  {num}. </font>{title}", st["section"])


def _info_table(summary: dict, st: dict):
    rows = []
    items = list(summary.items())
    for i in range(0, len(items), 2):
        row = []
        for j in range(2):
            if i + j < len(items):
                k, v = items[i + j]
                label = KEY_LABELS.get(k, k)
                cell = Paragraph(
                    f"<font color='#8E8E93' size='7'>{label}</font><br/>"
                    f"<font size='9'>{v or '—'}</font>",
                    st["body"],
                )
            else:
                cell = Paragraph("", st["body"])
            row.append(cell)
        rows.append(row)

    tbl = Table(rows, colWidths=[85 * mm, 85 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F5F7")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#F5F5F7"), colors.HexColor("#EBEBF0")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.white),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return tbl


def _risk_table(r: dict, st: dict):
    level  = r.get("risk_level", "low")
    color  = _RISK_COLOR.get(level, colors.HexColor("#007AFF"))
    bg     = _RISK_BG.get(level, colors.HexColor("#F0F6FF"))
    label  = _RISK_LABEL.get(level, level)
    rtype  = r.get("risk_type", "")
    llm_expl = (r.get("llm_explanation") or "").strip()
    static_expl = r.get("explanation", "")
    expl = llm_expl or static_expl
    evid   = (r.get("evidence_sentence") or "")[:100]
    expl_tag = "AI Analysis" if llm_expl else "Static Analysis"

    content = Paragraph(
        f"<font color='{color.hexval()}' size='8'>[{label}]</font>  "
        f"<font size='9'><b>{rtype}</b></font><br/>"
        f"<font size='7.5' color='#8E8E93'><b>{expl_tag}</b></font><br/>"
        f"<font size='8' color='#444444'>{expl}</font>"
        + (f"<br/><font size='7.5' color='#8E8E93'><i>Evidence: {evid}...</i></font>" if evid else ""),
        st["body"],
    )
    tbl = Table([[content]], colWidths=[170 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LINEAFTER",     (0, 0), (0, -1), 3, color),
        ("LINEBEFORE",    (0, 0), (0, -1), 3, color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _missing_table(m: dict, st: dict):
    name  = m.get("item_name", "")
    desc  = m.get("description", "")
    risk  = m.get("potential_risk", "")
    orange = colors.HexColor("#FF9500")
    content = Paragraph(
        f"<font color='#FF9500' size='8'>&#9888; Missing: </font>"
        f"<font size='9'><b>{name}</b></font><br/>"
        f"<font size='8' color='#444444'>{desc}</font><br/>"
        f"<font size='7.5' color='#8E8E93'>Potential Risk: {risk}</font>",
        st["body"],
    )
    tbl = Table([[content]], colWidths=[170 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FFF8F0")),
        ("LINEAFTER",     (0, 0), (0, -1), 3, orange),
        ("LINEBEFORE",    (0, 0), (0, -1), 3, orange),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return tbl


def build_pdf_bytes(
    contract_id: int,
    summary: dict,
    risks: list,
    missing_items: list,
) -> tuple[bytes, str, str]:
    """返回 (pdf_bytes, mimetype, filename)。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    buf = BytesIO()
    st  = _styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"ContractGuard Contract Analysis Report #{contract_id}",
        author="ContractGuard",
    )

    blue = colors.HexColor("#0071E3")
    story = []

    # ── Header ────────────────────────────────────────────────
    story.append(Paragraph("ContractGuard", st["logo"]))
    story.append(Paragraph("Contract Risk Analysis Report", st["subtitle"]))
    story.append(Paragraph(f"Generated: {now}", st["meta"]))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=blue, spaceAfter=10))

    # ── Section 1: Key Information Summary ────────────────────
    story.append(_section_header("1", "Key Information Summary", st))
    if summary:
        story.append(_info_table(summary, st))
    else:
        story.append(Paragraph("No summary information available.", st["small"]))
    story.append(Spacer(1, 6 * mm))

    # ── Section 2: Risk Clause Detection ──────────────────────
    story.append(_section_header("2", "Risk Clause Detection", st))
    if risks:
        for r in risks:
            story.append(_risk_table(r, st))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("&#10003;  No risk clauses detected.", st["ok"]))
    story.append(Spacer(1, 4 * mm))

    # ── Section 3: Missing Clause Detection ───────────────────
    story.append(_section_header("3", "Missing Clause Detection", st))
    if missing_items:
        for m in missing_items:
            story.append(_missing_table(m, st))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("&#10003;  All essential clauses are present.", st["ok"]))

    # ── Disclaimer ────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.4,
                             color=colors.HexColor("#E5E5EA"), spaceAfter=6))
    story.append(Paragraph(
        "&#9888; Disclaimer: This report is automatically generated by ContractGuard System "
        "for reference purposes only and does not constitute formal legal advice. "
        "For significant contract disputes, please consult a qualified legal professional.",
        st["disclaimer"],
    ))

    doc.build(story)
    return (
        buf.getvalue(),
        "application/pdf",
        f"ContractGuard_Report_{contract_id}.pdf",
    )
