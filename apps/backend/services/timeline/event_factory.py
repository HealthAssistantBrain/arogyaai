from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_report_event_payload(report: Any) -> dict[str, Any]:
    summary_data = report.summary_data if isinstance(getattr(report, "summary_data", None), dict) else {}
    upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
    filename = (
        getattr(report, "original_filename", None)
        or upload_metadata.get("original_filename")
        or upload_metadata.get("file_name")
        or getattr(report, "stored_filename", None)
        or "Medical report"
    )
    report_type = report.report_type.value if hasattr(report.report_type, "value") else str(report.report_type)
    status = report.status.value if hasattr(report.status, "value") else str(report.status)
    summary_lines = summary_data.get("summary") if isinstance(summary_data.get("summary"), list) else []
    summary = _clean_text(summary_lines[0] if summary_lines else None) or f"{report_type.replace('_', ' ').title()} uploaded for review."

    return {
        "user_id": report.user_id,
        "type": "report",
        "event_type": "report_uploaded",
        "source_type": "report",
        "source_id": report.id,
        "reference_id": report.id,
        "title": "Medical report uploaded",
        "summary": summary,
        "timestamp": report.created_at or datetime.now(timezone.utc),
        "metadata": {
            "report_id": str(report.id),
            "filename": filename,
            "original_filename": getattr(report, "original_filename", None) or upload_metadata.get("original_filename"),
            "stored_filename": getattr(report, "stored_filename", None) or upload_metadata.get("stored_filename"),
            "file_url": getattr(report, "file_url", None),
            "report_type": report_type,
            "status": status,
            "source": "report upload",
            "url": "/medical-reports",
        },
    }


def build_symptom_analysis_event_payload(session: Any) -> dict[str, Any]:
    severity = f"{session.severity}/10" if getattr(session, "severity", None) is not None else None
    return {
        "user_id": session.user_id,
        "type": "Symptom Analysis",
        "event_type": "symptom_analysis",
        "source_type": "symptom_analysis",
        "source_id": session.id,
        "reference_id": session.id,
        "title": session.chief_complaint or "Symptom analysis saved",
        "summary": session.ai_summary or "AI symptom analysis saved to timeline.",
        "severity": severity,
        "confidence": getattr(session, "confidence_score", None),
        "timestamp": session.created_at,
        "metadata": {
            "category": "symptom",
            "source": "ai symptom analysis",
            "analysis_id": str(session.id),
            "summary": session.ai_summary,
            "severity": severity,
            "risk_level": session.risk_level,
            "urgency_level": session.urgency_level,
            "possible_causes": _safe_list(getattr(session, "possible_causes", None)),
            "recommendations": _safe_list(getattr(session, "recommendations", None)),
            "red_flags": _safe_list(getattr(session, "red_flags", None)),
            "description": session.ai_summary or "AI symptom analysis saved to timeline.",
            "url": "/symptom-analysis",
        },
    }


def build_generated_report_event_payload(generated_report: Any) -> dict[str, Any]:
    payload = generated_report.report_payload if isinstance(getattr(generated_report, "report_payload", None), dict) else {}
    sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    first_section = sections[0] if sections else {}
    first_content = first_section.get("content", [None]) if isinstance(first_section, dict) else [None]
    summary = _clean_text(getattr(generated_report, "summary", None)) or _clean_text(first_content[0] if isinstance(first_content, list) else None)

    return {
        "user_id": generated_report.user_id,
        "type": "AI Report",
        "event_type": "generated_report",
        "source_type": "report_generation",
        "source_id": generated_report.id,
        "reference_id": generated_report.id,
        "title": generated_report.title,
        "summary": summary or "AI-generated longitudinal report created.",
        "confidence": getattr(generated_report, "confidence_score", None),
        "timestamp": generated_report.created_at,
        "metadata": {
            "category": "report_generation",
            "source": "ai report generation",
            "generated_report_id": str(generated_report.id),
            "summary": summary,
            "recommendations": _safe_list(getattr(generated_report, "recommendations", None)),
            "description": summary or "AI-generated longitudinal report created.",
            "url": "/report-generation",
        },
    }
