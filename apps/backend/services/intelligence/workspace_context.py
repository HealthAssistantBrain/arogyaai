from __future__ import annotations

from typing import Any


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_number(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_feature_value(feature_payload: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _to_number(feature_payload.get(key))
        if value is not None:
            return value
    return None


def summarize_selected_reports(reports: list[dict[str, Any]]) -> list[str]:
    highlights: list[str] = []
    for report in reports[:4]:
        file_name = _clean_text(report.get("file_name") or report.get("title") or "Medical report")
        report_type = _clean_text(report.get("report_type") or "report").replace("_", " ").title()
        excerpt = _clean_text(report.get("summary_excerpt"))
        if excerpt:
            highlights.append(f"{report_type}: {file_name} suggests {excerpt}")
        else:
            highlights.append(f"{report_type}: {file_name} is available for longitudinal correlation.")
    return highlights


def summarize_selected_symptom_sessions(sessions: list[dict[str, Any]]) -> list[str]:
    highlights: list[str] = []
    for session in sessions[:4]:
        complaint = _clean_text(session.get("chief_complaint") or session.get("title") or "Symptom session")
        risk = _clean_text(session.get("risk_level") or session.get("analysis", {}).get("risk_level"))
        summary = _clean_text(session.get("summary") or session.get("analysis", {}).get("summary"))
        if summary and risk:
            highlights.append(f"{complaint}: {summary} Risk signal recorded as {risk}.")
        elif summary:
            highlights.append(f"{complaint}: {summary}")
        else:
            highlights.append(f"{complaint}: structured symptom reasoning is available for the report.")
    return highlights


def build_symptom_workspace_context(
    *,
    request_payload: dict[str, Any],
    feature_payload: dict[str, Any],
    context_snapshot: dict[str, Any],
) -> dict[str, Any]:
    wearable_correlations: list[str] = []
    timeline_correlations: list[str] = []
    recent_reports = _safe_list(context_snapshot.get("recent_reports"))
    latest_history = _safe_dict(context_snapshot.get("latest_clinical_history"))

    sleep_hours = _find_feature_value(feature_payload, ["sleep_hours", "sleep_duration", "sleep"])
    steps = _find_feature_value(feature_payload, ["steps", "daily_steps"])
    resting_hr = _find_feature_value(feature_payload, ["resting_heart_rate", "heart_rate", "avg_heart_rate"])
    spo2 = _find_feature_value(feature_payload, ["spo2", "oxygen_saturation"])

    if sleep_hours is not None:
        wearable_correlations.append(f"Recent sleep trend is {sleep_hours:.1f} hours, which may influence fatigue, headache, and recovery patterns.")
    if steps is not None:
        wearable_correlations.append(f"Activity signal is {steps:.0f} steps, which helps contextualize exertional or low-energy complaints.")
    if resting_hr is not None:
        wearable_correlations.append(f"Heart-rate context is around {resting_hr:.0f} bpm and can help frame palpitations, stress, or cardiopulmonary symptoms.")
    if spo2 is not None:
        wearable_correlations.append(f"Available oxygen-saturation context is {spo2:.0f}%, useful when breathlessness or chest symptoms are reported.")
    if not wearable_correlations:
        wearable_correlations.append("No recent wearable metrics were available, so the analysis leans more heavily on structured symptom detail and stored history.")

    for item in summarize_selected_reports(recent_reports):
        timeline_correlations.append(item)

    if latest_history:
        complaint = _clean_text(latest_history.get("chief_complaint") or latest_history.get("title"))
        created_at = _clean_text(latest_history.get("created_at"))
        if complaint:
            readable_date = created_at[:10] if created_at else "a recent session"
            timeline_correlations.append(f"A prior clinical-history entry for {complaint.lower()} exists from {readable_date}, helping longitudinal comparison.")

    if not timeline_correlations:
        timeline_correlations.append("No strong timeline correlations were available yet; this session becomes a fresh anchor point in the longitudinal record.")

    return {
        "wearable_correlations": wearable_correlations[:4],
        "timeline_correlations": timeline_correlations[:4],
        "input_snapshot": {
            "chief_complaint": _clean_text(request_payload.get("chief_complaint")),
            "symptom_count": len(_safe_list(request_payload.get("associated_symptoms"))),
        },
    }


def build_report_workspace_brief(
    *,
    timeline_events: list[dict[str, Any]],
    selected_reports: list[dict[str, Any]],
    selected_symptom_sessions: list[dict[str, Any]],
    include_wearables: bool,
) -> dict[str, Any]:
    report_highlights = summarize_selected_reports(selected_reports)
    symptom_highlights = summarize_selected_symptom_sessions(selected_symptom_sessions)
    wearable_highlights: list[str] = []

    if include_wearables:
        for event in timeline_events:
            event_type = _clean_text(event.get("type") or event.get("event_type")).lower()
            if event_type == "vitals":
                description = _clean_text(event.get("description"))
                if description:
                    wearable_highlights.append(description)
            if len(wearable_highlights) >= 4:
                break

    timeline_span = {
        "start": timeline_events[0].get("event_date") if timeline_events else None,
        "end": timeline_events[-1].get("event_date") if timeline_events else None,
        "event_count": len(timeline_events),
    }

    return {
        "report_highlights": report_highlights,
        "symptom_highlights": symptom_highlights,
        "wearable_highlights": wearable_highlights[:4],
        "timeline_span": timeline_span,
    }
