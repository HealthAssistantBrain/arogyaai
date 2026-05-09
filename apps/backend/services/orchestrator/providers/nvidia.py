from __future__ import annotations

import os
from typing import Any

from .base import BaseAIProvider


class NvidiaProvider(BaseAIProvider):
    name = "nvidia"

    def is_available(self) -> bool:
        enabled = os.getenv("AI_ORCHESTRATOR_ENABLE_NVIDIA", "false").strip().lower() in {"1", "true", "yes", "on"}
        api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        return bool(enabled and api_key)

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        workflow: str = "generic",
    ) -> dict[str, Any] | None:
        raise NotImplementedError("NVIDIA provider routing is scaffolded but not enabled yet.")

    def describe(self) -> dict[str, Any]:
        return {
            **super().describe(),
            "status": "scaffolded_not_implemented",
        }
