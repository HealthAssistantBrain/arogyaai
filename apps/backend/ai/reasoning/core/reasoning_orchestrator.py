from __future__ import annotations

from typing import Any

from ..schemas import ReasoningResponse
from .cognitive_engine import CognitiveEngine


class ReasoningOrchestrator:
    def __init__(self) -> None:
        self.engine = CognitiveEngine()

    def generate(self, **kwargs: Any) -> dict[str, Any]:
        response = self.engine.generate(**kwargs)
        return response.model_dump(mode="json")


_ORCHESTRATOR: ReasoningOrchestrator | None = None


def get_reasoning_orchestrator() -> ReasoningOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = ReasoningOrchestrator()
    return _ORCHESTRATOR
