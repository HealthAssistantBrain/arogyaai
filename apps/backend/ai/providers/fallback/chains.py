from __future__ import annotations

from typing import Any

from ..models.payloads import ProviderCandidate, ProviderRequest
from ..routing.task_registry import TaskRoutingPolicy


class FallbackChainBuilder:
    def build(
        self,
        request: ProviderRequest,
        *,
        policy: TaskRoutingPolicy,
        available_providers: set[str],
        provider_models: dict[str, list[str]],
    ) -> list[ProviderCandidate]:
        candidates: list[ProviderCandidate] = []
        ordered_providers = [policy.primary_provider, *policy.fallback_providers]
        preferred = [item for item in request.provider_preferences if item]
        if preferred:
            ordered_providers = [*preferred, *[item for item in ordered_providers if item not in preferred]]

        seen: set[tuple[str, str]] = set()
        for depth, provider in enumerate(ordered_providers):
            if provider not in available_providers:
                continue
            models = list(provider_models.get(provider) or [])
            preferred_models = list(models) if models else [policy.primary_model, *policy.fallback_models]
            for model in preferred_models:
                cleaned = str(model or "").strip()
                if not cleaned:
                    continue
                key = (provider, cleaned)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    ProviderCandidate(
                        provider=provider,
                        model=cleaned,
                        reason="fallback_chain",
                        task=request.task,
                        priority=len(candidates),
                        timeout_seconds=request.timeout_seconds or policy.latency_budget_seconds,
                        use_json_mode=request.require_structured_output or policy.require_structured_output,
                        use_streaming=request.require_streaming and provider in available_providers,
                        fallback_depth=depth,
                        metadata={"workflow": request.workflow},
                    )
                )
        return candidates
