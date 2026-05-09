from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .router import AIOrchestrator, OrchestratorRequest, get_orchestrator


__all__ = ["AIOrchestrator", "OrchestratorRequest", "get_orchestrator"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .router import AIOrchestrator, OrchestratorRequest, get_orchestrator

    exports = {
        "AIOrchestrator": AIOrchestrator,
        "OrchestratorRequest": OrchestratorRequest,
        "get_orchestrator": get_orchestrator,
    }
    return exports[name]
