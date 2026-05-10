from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


@dataclass(slots=True)
class WorkflowRouteDecision:
    workflow: str
    reason: str
    endpoint_type: str = ""
    intent: str = ""
    medical_complexity: str = "medium"
    latency_tier: str = "balanced"
    route_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowExecutionContext:
    workflow: str
    user_id: str
    request_id: str
    started_at: str
    query: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    route: WorkflowRouteDecision | None = None
    route_hints: dict[str, Any] = field(default_factory=dict)
    input_artifacts: list[dict[str, Any]] = field(default_factory=list)
    user_context: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    retrieved_knowledge: dict[str, Any] = field(default_factory=dict)
    workflow_metadata: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    execution_state: dict[str, Any] = field(default_factory=dict)
    confidence_metrics: dict[str, Any] = field(default_factory=dict)
    stage_timings_ms: dict[str, float] = field(default_factory=dict)
    retries: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
    validated_response: dict[str, Any] = field(default_factory=dict)
    formatted_output: dict[str, Any] = field(default_factory=dict)
    finalized_output: dict[str, Any] = field(default_factory=dict)
    persisted_memory: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    source: str = "ai_orchestrator"
    fallback_activated: bool = False
    cancelled: bool = False

    @classmethod
    def from_request(cls, request: Any) -> WorkflowExecutionContext:
        metadata = _safe_dict(getattr(request, "metadata", None))
        route_hints = _safe_dict(getattr(request, "route_hints", None) or metadata.get("route_hints"))
        uploaded_files = _safe_list(
            getattr(request, "uploaded_files", None)
            or metadata.get("uploaded_files")
            or route_hints.get("uploaded_files")
        )
        return cls(
            workflow=_text(getattr(request, "workflow", None), "generic"),
            user_id=_text(getattr(request, "user_id", None)),
            request_id=str(uuid.uuid4()),
            started_at=utc_now_iso(),
            query=_text(getattr(request, "query", None)),
            payload=_safe_dict(getattr(request, "payload", None)),
            metadata=metadata,
            route_hints=route_hints,
            input_artifacts=[item for item in uploaded_files if isinstance(item, dict)],
        )

    def record_stage(
        self,
        stage: str,
        *,
        duration_ms: float,
        status: str,
        attempt: int,
        error: str | None = None,
    ) -> None:
        self.stage_timings_ms[stage] = round(duration_ms, 2)
        self.retries[stage] = max(0, attempt - 1)
        if error:
            self.errors.append(
                {
                    "stage": stage,
                    "status": status,
                    "attempt": attempt,
                    "error": error,
                }
            )

    def attach_memory(self) -> None:
        if not self.user_context:
            self.memory = {}
            return
        self.memory = {
            "summary": _safe_list(self.user_context.get("memory_summary"))[:8],
            "conversation_state": _safe_dict(self.user_context.get("conversation_state")),
            "longitudinal_summary": _safe_dict(self.user_context.get("longitudinal_summary")),
            "continuity_summary": _safe_dict(self.user_context.get("continuity_summary")),
            "structured_context": _safe_dict(self.user_context.get("structured_context")),
            "health_history": _safe_dict(self.user_context.get("clinical_history")),
            "wearable_context": _safe_dict(self.user_context.get("wearable_trends")),
            "recent_reports": _safe_list(self.user_context.get("recent_reports"))[:4],
            "user_preferences": _safe_dict(self.user_context.get("preferences")),
        }
        self.workflow_metadata.setdefault("context_meta", _safe_dict(self.user_context.get("context_meta")))

    def current_output(self) -> dict[str, Any]:
        for candidate in (
            self.finalized_output,
            self.formatted_output,
            self.validated_response,
            self.raw_response,
        ):
            if isinstance(candidate, dict) and candidate:
                return candidate
        return {}

    def orchestration_summary(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "workflow": self.workflow,
            "status": self.status,
            "source": self.source,
            "fallback_activated": self.fallback_activated,
            "cancelled": self.cancelled,
            "started_at": self.started_at,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "retries": dict(self.retries),
            "provider": self.provider_metadata.get("provider"),
            "model": self.provider_metadata.get("model"),
            "provider_attempts": _safe_list(self.provider_metadata.get("attempts")),
            "retrieval_source": self.workflow_metadata.get("retrieval_source"),
            "timeline_events_generated": len(self.timeline_events),
            "route": {
                "workflow": self.route.workflow,
                "reason": self.route.reason,
                "endpoint_type": self.route.endpoint_type,
                "intent": self.route.intent,
                "medical_complexity": self.route.medical_complexity,
                "latency_tier": self.route.latency_tier,
            }
            if self.route
            else None,
            "partial_response_available": bool(self.current_output()),
            "errors": list(self.errors),
        }
