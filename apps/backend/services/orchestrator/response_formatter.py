from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResponseFormatter:
    @staticmethod
    def envelope(
        *,
        data: Any,
        workflow: str,
        status: str = "ready",
        source: str = "ai_orchestrator",
        provider: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "success": error is None,
            "status": status,
            "source": source,
            "error": error,
            "data": data,
            "workflow": workflow,
            "generated_at": utc_now_iso(),
        }
        if provider:
            payload["provider"] = provider
        return payload
