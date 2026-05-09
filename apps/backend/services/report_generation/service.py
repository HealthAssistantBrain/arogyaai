from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID
import uuid

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from models import GeneratedReport, Report, SymptomAnalysisSession, User
from services.intelligence import build_report_workspace_brief
from services.timeline import build_generated_report_event_payload
from services.timeline_service import build_timeline_events, create_timeline_event


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid timeline date.") from exc


def _timeline_window_filter(
    events: list[dict[str, Any]],
    *,
    start: date | None,
    end: date | None,
) -> list[dict[str, Any]]:
    if not start and not end:
        return events

    filtered: list[dict[str, Any]] = []
    for event in events:
        raw_value = event.get("event_date") or event.get("timestamp")
        if not raw_value:
            continue
        try:
            event_date = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00")).date()
        except ValueError:
            try:
                event_date = date.fromisoformat(str(raw_value)[:10])
            except ValueError:
                continue

        if start and event_date < start:
            continue
        if end and event_date > end:
            continue
        filtered.append(event)
    return filtered


class ReportGenerationService:
    @staticmethod
    def _serialize_report_source(report: Report) -> dict[str, Any]:
        summary_data = report.summary_data if isinstance(report.summary_data, dict) else {}
        upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
        summary_lines = summary_data.get("summary") if isinstance(summary_data.get("summary"), list) else []
        report_type = report.report_type.value if hasattr(report.report_type, "value") else str(report.report_type)
        status_value = report.status.value if hasattr(report.status, "value") else str(report.status)
        return {
            "id": str(report.id),
            "file_name": report.original_filename or report.stored_filename or "Medical report",
            "report_type": report_type,
            "status": status_value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "date_of_report": upload_metadata.get("date_of_report"),
            "summary_excerpt": _clean_text(summary_lines[0] if summary_lines else None),
        }

    @staticmethod
    def _serialize_symptom_source(session: SymptomAnalysisSession) -> dict[str, Any]:
        return {
            "id": str(session.id),
            "chief_complaint": session.chief_complaint,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "summary": session.ai_summary,
            "risk_level": session.risk_level,
            "urgency_level": session.urgency_level,
            "recommendations": _safe_list(session.recommendations),
        }

    @staticmethod
    def _confidence_score(
        *,
        report_count: int,
        symptom_count: int,
        timeline_count: int,
        wearable_count: int,
    ) -> float:
        score = 0.35
        score += min(report_count, 4) * 0.11
        score += min(symptom_count, 3) * 0.1
        score += min(timeline_count, 10) * 0.015
        score += min(wearable_count, 4) * 0.03
        return round(min(score, 0.96), 2)

    @staticmethod
    def _sections(
        *,
        title: str,
        brief: dict[str, Any],
        confidence_score: float,
    ) -> list[dict[str, Any]]:
        report_highlights = brief.get("report_highlights") or []
        symptom_highlights = brief.get("symptom_highlights") or []
        wearable_highlights = brief.get("wearable_highlights") or []
        timeline_span = brief.get("timeline_span") or {}
        event_count = timeline_span.get("event_count") or 0
        start = timeline_span.get("start") or "unknown start"
        end = timeline_span.get("end") or "unknown end"

        overview = [
            f"{title} synthesizes {len(report_highlights)} report sources, {len(symptom_highlights)} symptom sessions, and {event_count} longitudinal events.",
            f"Timeline coverage spans from {start} to {end}.",
            f"AI confidence for this synthesis is {int(confidence_score * 100)}% based on source completeness and cross-signal overlap.",
        ]
        patterns = report_highlights or ["No uploaded reports were selected, so the synthesis emphasizes symptom and timeline context."]
        symptoms = symptom_highlights or ["No dedicated symptom-analysis sessions were selected for this report."]
        wearables = wearable_highlights or ["Wearable context was not included or no recent vital patterns were available."]
        recommendations = [
            "Review this synthesized report with a qualified clinician before making treatment decisions.",
            "Compare AI findings with the underlying reports, symptom sessions, and medication history.",
            "Refresh the report after new uploads, symptom analyses, or wearable changes to keep longitudinal reasoning current.",
        ]

        return [
            {"title": "Executive Summary", "content": overview},
            {"title": "Report Correlations", "content": patterns},
            {"title": "Symptom Reasoning", "content": symptoms},
            {"title": "Wearable and Timeline Signals", "content": wearables},
            {"title": "Clinical Recommendations", "content": recommendations},
        ]

    @classmethod
    def _serialize_generated_report(cls, report: GeneratedReport) -> dict[str, Any]:
        payload = report.report_payload if isinstance(report.report_payload, dict) else {}
        source_snapshot = report.source_snapshot if isinstance(report.source_snapshot, dict) else {}
        confidence = report.confidence_score
        confidence_value = round(float(confidence), 2) if confidence is not None else None
        return {
            "id": str(report.id),
            "title": report.title,
            "status": report.status,
            "generation_type": report.generation_type,
            "summary": report.summary,
            "recommendations": _safe_list(report.recommendations),
            "confidence_score": confidence_value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "sources": source_snapshot,
            "report": payload,
            "timeline": {
                "saved_to_timeline": bool(report.timeline_event_id),
                "timeline_event_id": str(report.timeline_event_id) if report.timeline_event_id else None,
            },
            "export": {
                "pdf_endpoint": f"/api/v1/report-generation/{report.id}/export",
            },
        }

    @classmethod
    def generate(cls, db: Session, current_user: User, payload: Any) -> dict[str, Any]:
        request_payload = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload or {})
        selected_report_ids = [_coerce_uuid(item) for item in request_payload.get("report_ids") or []]
        selected_report_ids = [item for item in selected_report_ids if item is not None]
        selected_symptom_ids = [_coerce_uuid(item) for item in request_payload.get("symptom_session_ids") or []]
        selected_symptom_ids = [item for item in selected_symptom_ids if item is not None]

        reports_query = db.query(Report).filter(Report.user_id == current_user.id, Report.is_deleted == False)
        if selected_report_ids:
            reports_query = reports_query.filter(Report.id.in_(selected_report_ids))
        reports = reports_query.order_by(Report.created_at.desc()).limit(8).all()

        symptom_query = db.query(SymptomAnalysisSession).filter(SymptomAnalysisSession.user_id == current_user.id)
        if selected_symptom_ids:
            symptom_query = symptom_query.filter(SymptomAnalysisSession.id.in_(selected_symptom_ids))
        symptom_sessions = symptom_query.order_by(SymptomAnalysisSession.created_at.desc()).limit(8).all()

        timeline_start = _parse_date(request_payload.get("timeline_start"))
        timeline_end = _parse_date(request_payload.get("timeline_end"))
        all_timeline_events = build_timeline_events(db, current_user.id, include_vitals=True, limit_per_type=40)
        timeline_events = _timeline_window_filter(all_timeline_events, start=timeline_start, end=timeline_end)

        source_reports = [cls._serialize_report_source(report) for report in reports]
        source_symptoms = [cls._serialize_symptom_source(session) for session in symptom_sessions]
        brief = build_report_workspace_brief(
            timeline_events=timeline_events,
            selected_reports=source_reports,
            selected_symptom_sessions=source_symptoms,
            include_wearables=bool(request_payload.get("include_wearables", True)),
        )
        confidence_score = cls._confidence_score(
            report_count=len(source_reports),
            symptom_count=len(source_symptoms),
            timeline_count=len(timeline_events),
            wearable_count=len(brief.get("wearable_highlights") or []),
        )
        title = _clean_text(request_payload.get("title")) or "AI Longitudinal Clinical Report"
        sections = cls._sections(title=title, brief=brief, confidence_score=confidence_score)
        summary = sections[0]["content"][0]
        recommendations = sections[-1]["content"]

        generated_report = GeneratedReport(
            user_id=current_user.id,
            title=title,
            status="ready",
            generation_type="longitudinal_summary",
            summary=summary,
            recommendations=recommendations,
            confidence_score=confidence_score,
            source_snapshot={
                "reports": source_reports,
                "symptom_sessions": source_symptoms,
                "timeline": {
                    "start": request_payload.get("timeline_start"),
                    "end": request_payload.get("timeline_end"),
                    "event_count": len(timeline_events),
                },
                "include_wearables": bool(request_payload.get("include_wearables", True)),
                "include_biomarkers": bool(request_payload.get("include_biomarkers", True)),
            },
            report_payload={
                "sections": sections,
                "brief": brief,
            },
        )
        db.add(generated_report)
        db.flush()

        timeline_event = create_timeline_event(db, build_generated_report_event_payload(generated_report), commit=False)
        generated_report.timeline_event_id = timeline_event.id
        db.commit()
        db.refresh(generated_report)
        return cls._serialize_generated_report(generated_report)

    @classmethod
    def history(cls, db: Session, current_user: User, *, limit: int = 10) -> list[dict[str, Any]]:
        rows = (
            db.query(GeneratedReport)
            .filter(GeneratedReport.user_id == current_user.id)
            .order_by(GeneratedReport.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [cls._serialize_generated_report(row) for row in rows]

    @classmethod
    def get_one(cls, db: Session, current_user: User, report_id: str) -> dict[str, Any]:
        resolved_id = _coerce_uuid(report_id)
        if resolved_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated report not found.")
        row = (
            db.query(GeneratedReport)
            .filter(GeneratedReport.user_id == current_user.id, GeneratedReport.id == resolved_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated report not found.")
        return cls._serialize_generated_report(row)

    @classmethod
    def export_pdf_bytes(cls, db: Session, current_user: User, report_id: str) -> tuple[bytes, str]:
        report = cls.get_one(db, current_user, report_id)
        pdf_bytes = cls._build_pdf(report)
        safe_name = Path(report.get("title") or "ai-report").stem.replace(" ", "-").lower() or "ai-report"
        return pdf_bytes, f"{safe_name}.pdf"

    @staticmethod
    def _build_pdf(report: dict[str, Any]) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.7 * inch,
            leftMargin=0.7 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch,
            title=report.get("title") or "AI Clinical Report",
            author="ArogyaAI",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Title"], textColor=colors.HexColor("#13082A"), fontSize=20, leading=24)
        body_style = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=13, textColor=colors.HexColor("#334155"))
        heading_style = ParagraphStyle("heading", parent=styles["Heading2"], fontSize=11.5, leading=14, textColor=colors.HexColor("#6143F4"))
        content: list[Any] = [
            Paragraph("ArogyaAI", ParagraphStyle("brand", parent=styles["Heading3"], textColor=colors.HexColor("#6143F4"))),
            Paragraph(report.get("title") or "AI Clinical Report", title_style),
            Spacer(1, 10),
            Paragraph(_clean_text(report.get("summary")) or "AI-generated longitudinal clinical synthesis.", body_style),
            Spacer(1, 12),
        ]

        for section in _safe_list(_safe_dict(report.get("report")).get("sections")):
            content.append(Paragraph(_clean_text(section.get("title") or "Section"), heading_style))
            items = [_clean_text(item) for item in _safe_list(section.get("content")) if _clean_text(item)]
            content.append(
                ListFlowable(
                    [ListItem(Paragraph(item, body_style), leftIndent=10) for item in items or ["No structured detail available."]],
                    bulletType="bullet",
                    leftIndent=15,
                )
            )
            content.append(Spacer(1, 8))

        document.build(content)
        return buffer.getvalue()
