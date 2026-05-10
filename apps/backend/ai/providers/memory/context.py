from __future__ import annotations

from typing import Any

from ..models.payloads import ProviderRequest


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


class MemoryContextManager:
    def enrich(self, request: ProviderRequest) -> ProviderRequest:
        context = dict(request.context)
        if request.memory:
            context.setdefault("memory", _safe_dict(request.memory))
        if request.rag_context:
            context.setdefault("rag_context", _safe_dict(request.rag_context))
        if request.conversation_history:
            context.setdefault("conversation_history", _safe_list(request.conversation_history)[-6:])
        context.setdefault("execution_meta", {})
        context["execution_meta"].update(
            {
                "request_id": request.request_id,
                "workflow": request.workflow,
                "task": request.task,
                "user_id": request.user_id,
            }
        )
        request.context = context
        return request
