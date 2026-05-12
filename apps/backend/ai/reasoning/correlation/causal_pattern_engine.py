from __future__ import annotations

import logging
from typing import Any

from ..schemas import NarrativeContext, ReasoningCard

logger = logging.getLogger("uvicorn.error")


class CausalPatternEngine:
    def interpret(self, context: NarrativeContext, correlations: list[ReasoningCard]) -> list[ReasoningCard]:
        logger.info(
            "[CAUSAL_CORRELATION] user_id=%s patterns=%s",
            context.user_id,
            len(correlations),
        )
        return correlations
