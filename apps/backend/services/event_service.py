"""
Event engine that converts system events into persisted notifications.
"""
from __future__ import annotations

import logging
from typing import Any

from services.notification_service import trigger_notification_sync

logger = logging.getLogger("event_service")

SUPPORTED_EVENTS = {
    "USER_LOGIN",
    "VITALS_UPDATED",
    "HEART_RATE_ALERT",
    "STEPS_MILESTONE",
    "SLEEP_ALERT",
    "DEVICE_CONNECTED",
    "AI_INSIGHT_GENERATED",
    "LAB_RESULT_ABNORMAL",
    "REMINDER_TRIGGERED",
    "HEALTH_ALERT_GENERATED",
}


def _coerce_payload(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return dict(payload)
    return {"value": payload}


def _coerce_metric_value(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                continue
    return None


def emit_event(event_type: str, user_id: Any, payload: dict | Any | None = None) -> dict[str, Any] | None:
    normalized_event = str(event_type or "").strip().upper()
    if normalized_event not in SUPPORTED_EVENTS:
        logger.warning("[Events] Unsupported event type: %s", event_type)
        return None

    event_payload = _coerce_payload(payload)
    try:
        base_metadata = {"source_event": normalized_event, "payload": event_payload}

        if normalized_event == "USER_LOGIN":
            return trigger_notification_sync(
                str(user_id),
                "system",
                "Login detected",
                "We detected a login to your ArogyaAI account.",
                data=base_metadata,
            )

        if normalized_event == "VITALS_UPDATED":
            return trigger_notification_sync(
                str(user_id),
                "system",
                "Vitals synced successfully",
                "Your latest health data was saved.",
                data={**base_metadata, "url": "/timeline"},
            )

        if normalized_event == "DEVICE_CONNECTED":
            return trigger_notification_sync(
                str(user_id),
                "system",
                "Google Fit connected",
                "Your Google Fit account is connected.",
                data={**base_metadata, "url": "/settings/devices"},
            )

        if normalized_event == "AI_INSIGHT_GENERATED":
            risk_level = str(event_payload.get("risk_level") or "updated").upper()
            risk_score = event_payload.get("risk_score")
            score_text = ""
            try:
                if risk_score is not None:
                    score_text = f" Risk score: {float(risk_score):.2f}."
            except (TypeError, ValueError):
                score_text = ""
            summary = str(event_payload.get("summary") or "Your latest predictive insight is ready.")
            return trigger_notification_sync(
                str(user_id),
                "ai_insight",
                f"AI insight ready: {risk_level}",
                f"{summary}{score_text}",
                data={**base_metadata, "summary": summary, "url": "/insights"},
            )

        if normalized_event == "LAB_RESULT_ABNORMAL":
            abnormal_count = int(event_payload.get("abnormal_count") or 0)
            abnormal_names = event_payload.get("abnormal_names") or []
            abnormal_list = ", ".join(str(item) for item in abnormal_names[:4] if item)
            description = (
                f"{abnormal_count} abnormal lab result{'s' if abnormal_count != 1 else ''} detected."
                if abnormal_count
                else "Abnormal lab result detected."
            )
            if abnormal_list:
                description = f"{description} Review: {abnormal_list}."
            return trigger_notification_sync(
                str(user_id),
                "health_alert",
                "Abnormal lab results detected",
                description,
                data={**base_metadata, "severity": "warning", "url": "/lab-results"},
            )

        if normalized_event == "REMINDER_TRIGGERED":
            title = str(event_payload.get("title") or "Health reminder")
            description = str(event_payload.get("description") or "You have an upcoming health-related reminder.")
            return trigger_notification_sync(
                str(user_id),
                "appointment",
                title,
                description,
                data={**base_metadata, "url": event_payload.get("url") or "/notifications"},
            )

        if normalized_event == "HEALTH_ALERT_GENERATED":
            title = str(event_payload.get("title") or "Health alert")
            description = str(event_payload.get("description") or "A new health alert was generated.")
            severity = str(event_payload.get("severity") or "warning").lower()
            return trigger_notification_sync(
                str(user_id),
                "health_alert",
                title,
                description,
                data={**base_metadata, "severity": severity, "url": "/notifications"},
            )

        if normalized_event == "HEART_RATE_ALERT":
            heart_rate = _coerce_metric_value(event_payload, "heart_rate", "value", "bpm")
            if heart_rate is None or not (heart_rate > 110 or heart_rate < 45):
                return None
            return trigger_notification_sync(
                str(user_id),
                "health_alert",
                "Heart rate alert",
                f"Heart rate is {heart_rate:g} bpm.",
                data={**base_metadata, "severity": "critical", "url": "/timeline"},
            )

        if normalized_event == "STEPS_MILESTONE":
            steps = _coerce_metric_value(event_payload, "steps", "value")
            if steps is None or steps <= 8000:
                return None
            return trigger_notification_sync(
                str(user_id),
                "activity",
                "Steps milestone reached",
                f"You reached {int(steps):,} steps.",
                data={**base_metadata, "url": "/timeline"},
            )

        if normalized_event == "SLEEP_ALERT":
            sleep_hours = _coerce_metric_value(event_payload, "sleep", "value", "hours")
            if sleep_hours is None or sleep_hours >= 5:
                return None
            return trigger_notification_sync(
                str(user_id),
                "health_alert",
                "Sleep alert",
                f"You slept for {sleep_hours:g} hours.",
                data={**base_metadata, "severity": "warning", "url": "/sleep"},
            )

        return None
    except Exception:
        logger.exception("[Events] Failed to emit event=%s for user=%s", normalized_event, user_id)
        return None
