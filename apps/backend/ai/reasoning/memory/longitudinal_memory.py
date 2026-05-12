from __future__ import annotations

import logging
from typing import Any

from ..schemas import NarrativeContext

logger = logging.getLogger("uvicorn.error")


class LongitudinalMemory:
    def build(self, context: NarrativeContext) -> dict[str, Any]:
        payload = {
            "major_trends": context.memory.get("major_trends") or [],
            "abnormal_changes": context.memory.get("abnormal_changes") or [],
            "persistent_issues": context.memory.get("persistent_issues") or [],
        }
        logger.info(
            "[LONGITUDINAL_MEMORY] user_id=%s major_trends=%s persistent=%s",
            context.user_id,
            len(payload["major_trends"]),
            len(payload["persistent_issues"]),
        )
        return payload
