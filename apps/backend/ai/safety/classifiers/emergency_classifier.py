from __future__ import annotations

import re
from typing import Any


_EMERGENCY_PATTERNS: dict[str, tuple[str, ...]] = {
    "self_harm": (
        r"\b(suicid(?:e|al)|kill myself|hurt myself|end my life|self harm)\b",
    ),
    "cardiac": (
        r"\b(chest pain|chest pressure|pressure in chest|crushing chest pain)\b",
    ),
    "stroke": (
        r"\b(face droop|slurred speech|one[- ]sided weakness|stroke|arm weakness)\b",
    ),
    "respiratory": (
        r"\b(shortness of breath|trouble breathing|can't breathe|cannot breathe|breathing difficulty)\b",
    ),
    "bleeding": (
        r"\b(severe bleeding|bleeding heavily|won't stop bleeding)\b",
    ),
    "neurologic": (
        r"\b(unconscious|passed out|not waking up|seizure|convulsion)\b",
    ),
}


class EmergencyClassifier:
    def classify(self, *, query: str, text: str, conversation_history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        history_text = " ".join(
            str(item.get("content") or "")
            for item in (conversation_history or [])[-6:]
            if str(item.get("role") or "").strip().lower() == "user"
        )
        corpus = " ".join(part for part in (query, history_text, text) if str(part or "").strip())
        matches: list[str] = []
        tier = "none"
        for candidate_tier, patterns in _EMERGENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, corpus, flags=re.IGNORECASE):
                    matches.append(candidate_tier)
                    if tier == "none":
                        tier = candidate_tier
                    break
        return {
            "detected": bool(matches),
            "tier": tier,
            "matches": list(dict.fromkeys(matches)),
        }

    def escalation_message(self, tier: str) -> str:
        if tier == "self_harm":
            return (
                "This may be an emergency. Please call local emergency services now (such as 112/911) "
                "or reach out to an immediate crisis line like iCall or your local suicide hotline."
            )
        return (
            "This may need urgent medical attention. Please contact local emergency services now "
            "(such as 112/911) or go to the nearest emergency department."
        )
