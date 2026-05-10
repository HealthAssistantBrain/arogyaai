from __future__ import annotations

from typing import Any

from .router import route_message


class ConversationRouterOrchestrator:
    async def route_message(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None,
        user_context: dict[str, Any] | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await route_message(
            user_message,
            conversation_history,
            user_context,
            **kwargs,
        )
