from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderTaskRequest:
    task: str
    workflow: str
    prompt: str = ""
    system_prompt: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    rag_context: dict[str, Any] = field(default_factory=dict)
    provider_preferences: list[str] = field(default_factory=list)
    route_hints: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    require_structured_output: bool = True
    require_streaming: bool = False
    allow_fallback: bool = True
    user_id: str = ""


class ModelRegistryProviderGateway:
    def __init__(self, model_registry: Any):
        self.model_registry = model_registry

    async def generate(self, request: ProviderTaskRequest) -> dict[str, Any]:
        payload = await self.model_registry.generate_json(
            task=request.task,
            workflow=request.workflow,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            context=request.context,
            metadata=request.metadata,
            conversation_history=request.conversation_history,
            memory=request.memory,
            rag_context=request.rag_context,
            provider_preferences=request.provider_preferences,
            route_hints=request.route_hints,
            timeout_seconds=request.timeout_seconds,
            require_structured_output=request.require_structured_output,
            require_streaming=request.require_streaming,
            allow_fallback=request.allow_fallback,
            user_id=request.user_id,
        )
        if isinstance(payload, dict):
            payload.setdefault("task", request.task)
        return payload
