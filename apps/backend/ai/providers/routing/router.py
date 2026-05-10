from __future__ import annotations

from typing import Any

from ..fallback.chains import FallbackChainBuilder
from ..health.monitor import ProviderHealthMonitor
from ..models.payloads import ProviderCandidate, ProviderRequest
from ..registry.provider_registry import ProviderRegistry
from .task_registry import TaskRoutingPolicy, build_task_policy


class ProviderRouter:
    def __init__(self, *, registry: ProviderRegistry, health_monitor: ProviderHealthMonitor) -> None:
        self.registry = registry
        self.health_monitor = health_monitor
        self.fallbacks = FallbackChainBuilder()

    def route(self, request: ProviderRequest) -> tuple[TaskRoutingPolicy, list[ProviderCandidate], dict[str, Any]]:
        policy = build_task_policy(request.task, workflow=request.workflow)
        if request.require_streaming:
            policy.prefer_streaming = True

        available_providers = self.registry.available_provider_names()
        provider_models = self.registry.available_models()

        if request.metadata.get("demo_mode") or request.route_hints.get("demo_mode"):
            policy.primary_provider = "ollama" if "ollama" in available_providers else policy.primary_provider
        if request.metadata.get("offline_mode") or request.route_hints.get("offline_mode"):
            policy.primary_provider = "ollama"
        if provider_models.get(policy.primary_provider):
            policy.primary_model = str(provider_models[policy.primary_provider][0] or policy.primary_model)

        candidates = self.fallbacks.build(
            request,
            policy=policy,
            available_providers=available_providers,
            provider_models=provider_models,
        )

        candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.fallback_depth,
                -self.health_monitor.score(candidate.provider),
                candidate.priority,
            ),
        )
        routing_meta = {
            "task": request.task,
            "workflow": request.workflow,
            "primary_provider": policy.primary_provider,
            "provider_preferences": list(request.provider_preferences),
            "require_streaming": request.require_streaming,
            "require_structured_output": request.require_structured_output,
            "candidate_count": len(candidates),
            "degraded_mode": any(self.health_monitor.is_quarantined(candidate.provider) for candidate in candidates),
        }
        return policy, candidates, routing_meta
