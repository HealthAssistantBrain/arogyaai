from __future__ import annotations

import logging
from typing import Any

from ..schemas import NarrativeContext, ReasoningCard

logger = logging.getLogger("uvicorn.error")


class PreventiveReasoning:
    def analyze(self, context: NarrativeContext, *, cards: list[ReasoningCard], temporal: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            "[PREVENTIVE_REASONING] user_id=%s trend_state=%s signals=%s",
            context.user_id,
            temporal.get("trend_state"),
            len(cards),
        )
        focus = "Maintain routine stability."
        if cards:
            focus = cards[0].recommendations[0] if cards[0].recommendations else cards[0].summary
        return {
            "focus": focus,
            "summary": "Preventive guidance is prioritized around the signals that are furthest from baseline and most likely to influence the next few days.",
        }
