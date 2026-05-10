from __future__ import annotations

import re
from typing import Any


CASUAL_TO_MEDICAL = (
    "is this normal",
    "diagnosed with",
    "condition",
    "pain",
    "hurts",
    "ache",
    "pressure",
    "dizziness",
    "shortness of breath",
    "breathless",
)

MEDICAL_TO_EMERGENCY = (
    "can't breathe",
    "cannot breathe",
    "crushing chest pain",
    "numb arm",
    "having a stroke",
    "having a heart attack",
    "unbearable",
    "can't move",
    "cannot move",
)

BODY_PART_PATTERN = re.compile(r"\b(chest|head|arm|leg|stomach|abdomen|back|throat|neck|heart|lung)\b")
DISCOMFORT_PATTERN = re.compile(r"\b(pain|hurt|hurts|pressure|ache|tightness|burning|dizzy|weak|numb)\b")
TIME_INTENSITY_PATTERN = re.compile(r"\b(since hours|for hours|all day|severe|worst|unbearable|sudden)\b")


def _clean_text(value: Any) -> str:
    return str(value or "").strip().lower()


def detect_escalation(
    user_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
    current_mode: str = "casual",
) -> dict[str, Any]:
    query = _clean_text(user_message)
    prior_text = " ".join(
        _clean_text(item.get("content"))
        for item in (conversation_history or [])[-4:]
        if isinstance(item, dict) and _clean_text(item.get("role")) == "user"
    )
    combined = f"{prior_text} {query}".strip()

    emergency = any(signal in combined for signal in MEDICAL_TO_EMERGENCY)
    if emergency or ("chest pain" in combined and "can't breathe" in combined):
        return {
            "escalated": True,
            "severity": "emergency",
            "target_mode": "medical",
            "reason": "emergency_signal_detected",
            "critical": True,
        }

    if current_mode == "casual":
        if any(signal in query for signal in CASUAL_TO_MEDICAL):
            return {
                "escalated": True,
                "severity": "medical",
                "target_mode": "medical",
                "reason": "medical_signal_detected",
                "critical": False,
            }
        if BODY_PART_PATTERN.search(query) and DISCOMFORT_PATTERN.search(query):
            return {
                "escalated": True,
                "severity": "medical",
                "target_mode": "medical",
                "reason": "body_discomfort_detected",
                "critical": False,
            }

    if current_mode == "medical" and TIME_INTENSITY_PATTERN.search(query) and DISCOMFORT_PATTERN.search(combined):
        return {
            "escalated": True,
            "severity": "emergency",
            "target_mode": "medical",
            "reason": "severity_intensified",
            "critical": True,
        }

    return {
        "escalated": False,
        "severity": "none",
        "target_mode": current_mode,
        "reason": "",
        "critical": False,
    }
