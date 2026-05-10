from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


@dataclass(slots=True)
class ProviderAttempt:
    provider: str
    model: str
    status: str
    latency_ms: float = 0.0
    error: str | None = None
    attempt: int = 1
    retry_count: int = 0
    fallback_depth: int = 0
    degraded: bool = False
    streamed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "latency_ms": round(float(self.latency_ms or 0.0), 2),
            "error": self.error,
            "attempt": self.attempt,
            "retry_count": self.retry_count,
            "fallback_depth": self.fallback_depth,
            "degraded": self.degraded,
            "streamed": self.streamed,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(slots=True)
class ProviderCandidate:
    provider: str
    model: str
    reason: str
    task: str
    priority: int = 0
    timeout_seconds: float | None = None
    use_json_mode: bool = True
    use_streaming: bool = False
    fallback_depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderRequest:
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
    max_retries: int = 1
    require_structured_output: bool = True
    require_streaming: bool = False
    allow_fallback: bool = True
    user_id: str = ""
    request_id: str = field(default_factory=lambda: uuid4().hex[:12])

    @classmethod
    def from_legacy(
        cls,
        *,
        task: str,
        workflow: str,
        prompt: str = "",
        system_prompt: str = "",
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        memory: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
        provider_preferences: list[str] | None = None,
        route_hints: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 1,
        require_structured_output: bool = True,
        require_streaming: bool = False,
        allow_fallback: bool = True,
        user_id: str = "",
    ) -> ProviderRequest:
        return cls(
            task=_safe_text(task, "generic"),
            workflow=_safe_text(workflow, "generic"),
            prompt=_safe_text(prompt),
            system_prompt=_safe_text(system_prompt),
            context=_safe_dict(context),
            metadata=_safe_dict(metadata),
            conversation_history=[item for item in _safe_list(conversation_history) if isinstance(item, dict)],
            memory=_safe_dict(memory),
            rag_context=_safe_dict(rag_context),
            provider_preferences=[_safe_text(item).lower() for item in _safe_list(provider_preferences) if _safe_text(item)],
            route_hints=_safe_dict(route_hints),
            timeout_seconds=timeout_seconds,
            max_retries=max(0, int(max_retries)),
            require_structured_output=require_structured_output,
            require_streaming=require_streaming,
            allow_fallback=allow_fallback,
            user_id=_safe_text(user_id),
        )


@dataclass(slots=True)
class ProviderResponse:
    success: bool
    provider: str
    model: str
    task: str
    workflow: str
    status: str
    content: dict[str, Any] = field(default_factory=dict)
    text: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    attempts: list[ProviderAttempt] = field(default_factory=list)
    latency_ms: float = 0.0
    tokens: dict[str, Any] = field(default_factory=dict)
    degraded: bool = False
    streamed: bool = False
    fallback_used: bool = False
    safe: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def as_legacy_result(self) -> dict[str, Any]:
        payload = dict(self.content)
        payload.setdefault("provider", self.provider)
        payload.setdefault("model", self.model)
        payload.setdefault("status", self.status)
        payload.setdefault("citations", self.citations)
        payload.setdefault("recommendations", self.recommendations)
        payload.setdefault("confidence_score", self.confidence)
        payload.setdefault("sections", self.sections)
        payload.setdefault("warnings", self.warnings)
        payload.setdefault("degraded", self.degraded)
        payload.setdefault("fallback_used", self.fallback_used)
        payload.setdefault("safe", self.safe)
        payload.setdefault("request_id", self.metadata.get("request_id"))
        payload.setdefault("routing", self.metadata.get("routing"))
        payload.setdefault("telemetry", self.metadata.get("telemetry"))
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "payload": payload,
            "attempts": [attempt.as_dict() for attempt in self.attempts],
            "degraded": self.degraded,
            "fallback_used": self.fallback_used,
            "safe": self.safe,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
            "tokens": dict(self.tokens),
        }
