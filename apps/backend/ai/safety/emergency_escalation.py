from __future__ import annotations

import logging
import re

from .clinical_rules import EMERGENCY_PATTERNS, ESCALATION_TEMPLATES
from .safety_types import ConversationContext, EmergencyReport

logger = logging.getLogger("arogyaai.safety.emergency")

_PRIORITY_ORDER = [
    "self_harm",
    "cardiac",
    "neurological",
    "respiratory",
    "allergic",
    "bleeding",
    "diabetic_emergency",
]


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    tier: _compile_patterns(patterns) for tier, patterns in EMERGENCY_PATTERNS.items()
}


def scan_for_emergency(
    user_input: str,
    ai_response: str,
    context: ConversationContext,
) -> EmergencyReport:
    try:
        search_corpus = _build_search_corpus(user_input, ai_response, context)
        matched_patterns: list[str] = []
        detected_tier: str | None = None

        for tier in _PRIORITY_ORDER:
            for pattern in _COMPILED_PATTERNS.get(tier, []):
                if pattern.search(search_corpus):
                    matched_patterns.append(f"{tier}:{pattern.pattern}")
                    detected_tier = detected_tier or tier
                    break

        if not detected_tier:
            return EmergencyReport(
                is_emergency=False,
                matched_patterns=[],
                tier="none",
                override_response=None,
            )

        override = ESCALATION_TEMPLATES.get(detected_tier, ESCALATION_TEMPLATES["general_emergency"])
        logger.warning(
            "Emergency detected",
            extra={
                "tier": detected_tier,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "matched": matched_patterns[:3],
            },
        )
        return EmergencyReport(
            is_emergency=True,
            matched_patterns=matched_patterns,
            tier=detected_tier,
            override_response=override,
        )
    except Exception as exc:
        logger.error("Emergency scanner failed: %s", exc, exc_info=True)
        return EmergencyReport(
            is_emergency=True,
            matched_patterns=["scanner_error_fallback"],
            tier="general_emergency",
            override_response=ESCALATION_TEMPLATES["general_emergency"],
        )


def _build_search_corpus(
    user_input: str,
    ai_response: str,
    context: ConversationContext,
) -> str:
    recent_history = " ".join(
        str(message.get("content") or "")
        for message in context.conversation_history[-6:]
        if str(message.get("role") or "").lower() == "user"
    )
    return f"{user_input} {user_input} {recent_history} {ai_response}".strip()
