from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND_PURPLE = colors.HexColor("#6143F4")
DEEP_INK = colors.HexColor("#13082A")
MUTED_TEXT = colors.HexColor("#64748B")
SOFT_BORDER = colors.HexColor("#E2E8F0")
SOFT_BG = colors.HexColor("#F8FAFC")
SUCCESS = colors.HexColor("#047857")
WARNING = colors.HexColor("#B45309")
DANGER = colors.HexColor("#BE123C")

DISCLAIMER = "AI-assisted report. Not a medical diagnosis."
DEFAULT_RECOMMENDATIONS = [
    "Review this summary with a qualified clinician before making medical decisions.",
    "Compare findings with symptoms, prior reports, and prescribed treatment plans.",
]


def generate_report_pdf_bytes(report: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.72 * inch,
        title="Clinical Report Summary",
        author="ArogyaAI",
        subject="AI-assisted clinical report summary",
    )

    styles = _styles()
    content: list[Any] = [
        _header(report, styles),
        Spacer(1, 16),
        _patient_section(report, styles),
        Spacer(1, 14),
    ]

    summary = _summary_lines(report)
    content.extend(_section("Summary", summary, styles, as_paragraphs=True))
    content.append(Spacer(1, 12))

    findings = _clinical_findings(report)
    content.extend(_section("Clinical Findings", findings, styles))
    content.append(Spacer(1, 12))

    content.extend(_risk_section(report, styles))
    content.append(Spacer(1, 12))

    recommendations = _recommendations(report)
    content.extend(_section("Recommendations", recommendations, styles))

    document.build(
        content,
        onFirstPage=_draw_footer,
        onLaterPages=_draw_footer,
    )
    return buffer.getvalue()


def build_report_pdf_filename(report: dict[str, Any]) -> str:
    stem = Path(_text(report.get("original_filename") or report.get("file_name") or report.get("name") or "clinical-report")).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "clinical-report"
    return f"{safe_stem}-clinical-summary.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "ArogyaBrand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=BRAND_PURPLE,
            alignment=TA_LEFT,
        ),
        "title": ParagraphStyle(
            "ClinicalTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=24,
            textColor=DEEP_INK,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=MUTED_TEXT,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=DEEP_INK,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#334155"),
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=MUTED_TEXT,
        ),
        "badge": ParagraphStyle(
            "Badge",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
    }


def _header(report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y")
    title_block = [
        Paragraph("ArogyaAI", styles["brand"]),
        Paragraph("Clinical Report Summary", styles["title"]),
        Paragraph(f"Generated {generated_at}", styles["meta"]),
    ]
    logo = Table(
        [[Paragraph("A", styles["badge"])]],
        colWidths=[36],
        rowHeights=[36],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PURPLE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0, BRAND_PURPLE),
            ]
        ),
    )
    report_type = _label(report.get("report_type") or report.get("reportType") or "Medical Report")
    status = _label(report.get("status") or "Ready")
    meta = Table(
        [
            [Paragraph("<b>Report Type</b>", styles["small"]), Paragraph(_escape(report_type), styles["small"])],
            [Paragraph("<b>Status</b>", styles["small"]), Paragraph(_escape(status), styles["small"])],
        ],
        colWidths=[72, 112],
        style=_info_table_style(),
    )
    table = Table([[logo, title_block, meta]], colWidths=[48, 300, 184])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, BRAND_PURPLE),
            ]
        )
    )
    return table


def _patient_section(report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    summary_view = _dict(report.get("summary_view"))
    patient = _patient_info(summary_view.get("patient_info"))
    upload_date = _format_date(report.get("date_of_report") or report.get("created_at") or report.get("createdAt"))
    file_name = _text(report.get("original_filename") or report.get("file_name") or report.get("name") or "Medical Report")
    rows = [
        [Paragraph("<b>File Name</b>", styles["small"]), Paragraph(_escape(file_name), styles["body"])],
        [Paragraph("<b>Upload Date</b>", styles["small"]), Paragraph(_escape(upload_date), styles["body"])],
        [Paragraph("<b>Patient</b>", styles["small"]), Paragraph(_escape(patient), styles["body"])],
    ]
    table = Table(rows, colWidths=[92, 416], style=_info_table_style())
    return KeepTogether([Paragraph("Patient Section", styles["section"]), table])


def _section(
    title: str,
    items: list[str],
    styles: dict[str, ParagraphStyle],
    *,
    as_paragraphs: bool = False,
) -> list[Any]:
    clean_items = [_clean_line(item) for item in items if _clean_line(item)]
    if not clean_items:
        clean_items = ["No structured details were available in this section."]

    block: list[Any] = [Paragraph(title, styles["section"])]
    if as_paragraphs:
        block.extend(Paragraph(_escape(item), styles["body"]) for item in clean_items)
        return block

    block.append(
        ListFlowable(
            [ListItem(Paragraph(_escape(item), styles["body"]), leftIndent=10) for item in clean_items],
            bulletType="bullet",
            start="circle",
            leftIndent=15,
            bulletFontSize=7,
            bulletOffsetY=1,
        )
    )
    return block


def _risk_section(report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    risk_level = _text(_dict(report.get("summary_view")).get("risk_level") or report.get("risk_level") or "Low")
    confidence = _confidence(report)
    tone = _risk_color(risk_level)
    rows = [
        [Paragraph("<b>Risk Level</b>", styles["small"]), Paragraph(_escape(_label(risk_level)), styles["body_bold"])],
        [Paragraph("<b>Confidence</b>", styles["small"]), Paragraph(_escape(confidence), styles["body"])],
    ]
    table = Table(rows, colWidths=[92, 416], style=_info_table_style(tone))
    notes = _risk_notes(report)
    return [Paragraph("Risk Analysis", styles["section"]), table, Spacer(1, 7), *_section("", notes, styles)[1:]]


def _draw_footer(canvas, document) -> None:
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(SOFT_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, 0.48 * inch, width - document.rightMargin, 0.48 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED_TEXT)
    canvas.drawString(document.leftMargin, 0.31 * inch, DISCLAIMER)
    canvas.drawRightString(width - document.rightMargin, 0.31 * inch, f"Page {document.page}")
    canvas.restoreState()


def _info_table_style(accent=BRAND_PURPLE) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
            ("BOX", (0, 0), (-1, -1), 0.7, SOFT_BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 2, accent),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, SOFT_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
    )


def _summary_lines(report: dict[str, Any]) -> list[str]:
    summary_view = _dict(report.get("summary_view"))
    structured_summary = _dict(report.get("structured_summary"))
    candidates = [
        summary_view.get("summary"),
        structured_summary.get("findings"),
        report.get("patient_summary"),
        report.get("summary"),
    ]
    return _first_lines(candidates, fallback=["Structured clinical summary was not available for this report."])


def _clinical_findings(report: dict[str, Any]) -> list[str]:
    summary_view = _dict(report.get("summary_view"))
    structured_summary = _dict(report.get("structured_summary"))
    findings = _lines(summary_view.get("key_findings") or structured_summary.get("findings") or report.get("summary"))
    abnormal = _format_named_values(summary_view.get("abnormal_values") or report.get("abnormal_values"))
    biomarkers = _format_named_values(summary_view.get("biomarkers") or report.get("markers"))
    notes = _lines(summary_view.get("notes"))
    return [*findings, *abnormal, *biomarkers[:6], *notes[:2]]


def _risk_notes(report: dict[str, Any]) -> list[str]:
    summary_view = _dict(report.get("summary_view"))
    risks = _lines(summary_view.get("risks") or report.get("risks"))
    if risks:
        return risks
    return ["No additional structured risk details were available beyond the overall risk level."]


def _recommendations(report: dict[str, Any]) -> list[str]:
    summary_view = _dict(report.get("summary_view"))
    lines = _lines(summary_view.get("recommendations") or report.get("recommendations"))
    return lines or DEFAULT_RECOMMENDATIONS


def _format_named_values(value: Any) -> list[str]:
    items = _list(value)
    formatted: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = _text(item.get("name") or item.get("label") or item.get("test") or item.get("title"))
            reading = _text(item.get("value") or item.get("reading") or item.get("result"))
            unit = _text(item.get("unit"))
            flag = _text(item.get("flag") or item.get("status") or item.get("trend"))
            pieces = [piece for piece in [reading, unit] if piece]
            value_text = " ".join(pieces)
            detail = " - ".join(piece for piece in [name, value_text, flag] if piece)
            if detail:
                formatted.append(detail)
        else:
            text = _clean_line(item)
            if text:
                formatted.append(text)
    return formatted


def _first_lines(candidates: list[Any], fallback: list[str]) -> list[str]:
    for candidate in candidates:
        lines = _lines(candidate)
        if lines:
            return lines
    return fallback


def _lines(value: Any) -> list[str]:
    if isinstance(value, dict):
        nested = value.get("findings") or value.get("key_findings") or value.get("notes") or value.get("summary")
        return _lines(nested)
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                lines.extend(_format_named_values([item]))
            else:
                lines.append(_clean_line(item))
        return [line for line in lines if line]
    text = _clean_line(value)
    if not text:
        return []
    split = [part.strip() for part in re.split(r"\n+|(?<=\.)\s+(?=[A-Z])", text) if part.strip()]
    return split or [text]


def _patient_info(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        labels = {
            "patient_name": "Name",
            "name": "Name",
            "age": "Age",
            "sex": "Sex",
            "gender": "Gender",
            "patient_id": "Patient ID",
            "report_date": "Report Date",
        }
        for key, raw in value.items():
            text = _text(raw)
            if text:
                parts.append(f"{labels.get(str(key), _label(key))}: {text}")
        return "; ".join(parts) or "Not specified in the uploaded report."
    return _text(value) or "Not specified in the uploaded report."


def _confidence(report: dict[str, Any]) -> str:
    summary_data = _dict(report.get("summary_data"))
    clinical_report = _dict(summary_data.get("clinical_report"))
    value = (
        report.get("confidence")
        or report.get("confidence_score")
        or summary_data.get("confidence")
        or summary_data.get("confidence_score")
        or clinical_report.get("confidence")
        or clinical_report.get("confidence_score")
        or report.get("ocr_confidence")
    )
    if value is None or value == "":
        return "Not specified"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if 0 <= number <= 1:
        return f"{number * 100:.0f}%"
    if 1 < number <= 100:
        return f"{number:.0f}%"
    return _text(value)


def _risk_color(risk_level: str):
    normalized = risk_level.strip().lower()
    if normalized in {"high", "critical", "severe"}:
        return DANGER
    if normalized in {"medium", "moderate", "elevated"}:
        return WARNING
    return SUCCESS


def _format_date(value: Any) -> str:
    if not value:
        return "Unknown date"
    text = _text(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.strftime("%b %d, %Y")


def _clean_line(value: Any) -> str:
    text = re.sub(r"\s+", " ", _text(value)).strip()
    if not text:
        return ""
    lowered = text.lower()
    raw_markers = [
        "raw ocr",
        "ocr text",
        "extracted text length",
        "no text could be extracted",
        "image ocr is not configured",
        "free mode currently supports direct text extraction",
    ]
    if any(marker in lowered for marker in raw_markers):
        return ""
    return text[:900]


def _label(value: Any) -> str:
    return re.sub(r"[_-]+", " ", _text(value)).strip().title()


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    return [value]


def _escape(value: Any) -> str:
    return html.escape(_text(value), quote=False)
