from __future__ import annotations

import os
import re
from typing import Any, Awaitable, Callable

from .depth_controller import depth_config


Regenerator = Callable[[str, list[str], dict[str, Any]], Awaitable[str] | str]


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", str(text or "")))


def contains_rag_citation(text: str) -> bool:
    lowered = str(text or "").lower()
    return bool(re.search(r"\[[0-9]+\]|\(source:|retrieved|citation|according to", lowered))


def contains_risk_score_mention(text: str) -> bool:
    lowered = str(text or "").lower()
    return "risk score" in lowered or "risk level" in lowered


def contains_blood_pressure_context(text: str) -> bool:
    lowered = str(text or "").lower()
    return "blood pressure" in lowered or "bp" in lowered


def count_disclaimers(text: str) -> int:
    lowered = str(text or "").lower()
    patterns = ("not a diagnosis", "seek medical care", "consult a doctor", "emergency services")
    return sum(lowered.count(pattern) for pattern in patterns)


def user_asked_about_risk(conversation_history: list[dict[str, Any]] | None) -> bool:
    history_text = " ".join(str(item.get("content") or "").lower() for item in (conversation_history or []) if isinstance(item, dict))
    return "risk score" in history_text or "risk" in history_text


def is_bp_conversation(conversation_history: list[dict[str, Any]] | None) -> bool:
    history_text = " ".join(str(item.get("content") or "").lower() for item in (conversation_history or []) if isinstance(item, dict))
    return "blood pressure" in history_text or "bp" in history_text


def _trim_to_words(text: str, limit: int | None) -> str:
    if not limit:
        return str(text or "").strip()
    words = re.findall(r"\S+", str(text or ""))
    if len(words) <= limit:
        return str(text or "").strip()
    trimmed = " ".join(words[:limit]).rstrip(",;:")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "."
    return trimmed


async def regenerate_with_constraint(
    response_text: str,
    issues: list[str],
    intent: dict[str, Any],
    *,
    regenerator: Regenerator | None = None,
) -> str:
    if regenerator is not None:
        regenerated = regenerator(response_text, issues, intent)
        if hasattr(regenerated, "__await__"):
            regenerated = await regenerated
        if isinstance(regenerated, str) and regenerated.strip():
            return regenerated.strip()

    cleaned = str(response_text or "")
    if "UNSOLICITED_RAG" in issues:
        cleaned = re.sub(r"\[[0-9]+\]", "", cleaned)
        cleaned = re.sub(r"\(source:[^)]+\)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"according to[^.]*\.", "", cleaned, flags=re.IGNORECASE)
    if "UNSOLICITED_RISK" in issues:
        cleaned = re.sub(r"[^.]*risk score[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^.]*risk level[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    if "UNSOLICITED_VITALS" in issues:
        cleaned = re.sub(r"[^.]*blood pressure[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    max_words = depth_config(str(intent.get("depth") or "")).get("max_words")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return _trim_to_words(cleaned, max_words)


async def apply_guardrails(
    response_text: str,
    intent: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
    *,
    regenerator: Regenerator | None = None,
    bypass: bool | None = None,
) -> str:
    if bypass is None:
        bypass = os.getenv("CHAT_GUARDRAILS_DISABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if bypass:
        return str(response_text or "").strip()

    issues: list[str] = []
    depth = str(intent.get("depth") or "")
    depth_limits = depth_config(depth)
    max_words = depth_limits.get("max_words")

    if depth in {"micro", "short"}:
        if max_words and count_words(response_text) > int(max_words):
            issues.append("OVER_LENGTH")
        if contains_rag_citation(response_text):
            issues.append("UNSOLICITED_RAG")
        if contains_risk_score_mention(response_text) and not user_asked_about_risk(conversation_history):
            issues.append("UNSOLICITED_RISK")
        if contains_blood_pressure_context(response_text) and not is_bp_conversation(conversation_history):
            issues.append("UNSOLICITED_VITALS")
        if count_disclaimers(response_text) > 1:
            issues.append("EXCESSIVE_DISCLAIMERS")
    elif max_words and count_words(response_text) > int(max_words):
        issues.append("OVER_LENGTH")

    if issues:
        return await regenerate_with_constraint(response_text, issues, intent, regenerator=regenerator)
    return str(response_text or "").strip()
