from __future__ import annotations

from typing import Any


DEPTH_CONFIG: dict[str, dict[str, Any]] = {
    "greeting": {"mode": "micro", "max_words": 20, "max_tokens": 40, "route_mode": "casual"},
    "acknowledgement": {"mode": "micro", "max_words": 15, "max_tokens": 30, "route_mode": "casual"},
    "gratitude": {"mode": "micro", "max_words": 15, "max_tokens": 30, "route_mode": "casual"},
    "farewell": {"mode": "micro", "max_words": 10, "max_tokens": 20, "route_mode": "casual"},
    "casual_chat": {"mode": "short", "max_words": 60, "max_tokens": 100, "route_mode": "casual"},
    "clarification": {"mode": "short", "max_words": 80, "max_tokens": 130, "route_mode": "casual"},
    "followup_question": {"mode": "medium", "max_words": 120, "max_tokens": 200, "route_mode": "medical"},
    "emotional_support": {"mode": "short", "max_words": 80, "max_tokens": 130, "route_mode": "medical"},
    "symptom_report": {"mode": "medium", "max_words": 180, "max_tokens": 300, "route_mode": "medical"},
    "emergency_concern": {"mode": "short", "max_words": 60, "max_tokens": 100, "route_mode": "medical"},
    "health_education": {"mode": "medium", "max_words": 200, "max_tokens": 330, "route_mode": "medical"},
    "risk_explanation": {"mode": "detailed", "max_words": 300, "max_tokens": 500, "route_mode": "medical"},
    "recommendation_request": {"mode": "detailed", "max_words": 250, "max_tokens": 400, "route_mode": "medical"},
    "report_analysis": {"mode": "expert", "max_words": None, "max_tokens": 1200, "route_mode": "expert"},
    "navigation_help": {"mode": "short", "max_words": 60, "max_tokens": 100, "route_mode": "casual"},
    "onboarding_help": {"mode": "short", "max_words": 80, "max_tokens": 130, "route_mode": "casual"},
}


def resolve_depth(intent_payload: dict[str, Any]) -> dict[str, Any]:
    intent = str(intent_payload.get("intent") or "casual_chat").strip().lower()
    config = DEPTH_CONFIG.get(intent, DEPTH_CONFIG["casual_chat"])
    resolved_mode = str(intent_payload.get("mode") or config["route_mode"]).strip().lower()
    return {
        **intent_payload,
        "depth": config["mode"],
        "mode": resolved_mode,
        "max_words": config["max_words"],
        "max_tokens": config["max_tokens"],
    }


def depth_config(depth: str) -> dict[str, Any]:
    for item in DEPTH_CONFIG.values():
        if item["mode"] == depth:
            return item
    return {"mode": depth, "max_words": None, "max_tokens": None}
