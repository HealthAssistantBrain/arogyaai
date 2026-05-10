from __future__ import annotations

import os
import logging
import time
from typing import Any

from ai.providers import get_provider_runtime
from ai.providers.models.payloads import ProviderRequest as RuntimeProviderRequest
from pipelines.rag_pipeline.config import RagSettings

from .providers.base import BaseAIProvider
from .providers.local import LocalOllamaProvider
from .providers.nvidia import NvidiaProvider
from .providers.openai import OpenAICompatibleProvider

logger = logging.getLogger("uvicorn.error")


class ModelRegistry:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.runtime = get_provider_runtime(self.settings)
        self._providers: dict[str, BaseAIProvider] = {
            "local": LocalOllamaProvider(self.settings),
            "openai": OpenAICompatibleProvider(self.settings),
            "nvidia": NvidiaProvider(),
        }
        self._default_provider_classes = {
            name: provider.__class__
            for name, provider in self._providers.items()
        }

    @property
    def providers(self) -> dict[str, BaseAIProvider]:
        return self._providers

    @providers.setter
    def providers(self, value: dict[str, BaseAIProvider]) -> None:
        self._providers = value

    def provider_order(self, workflow: str = "generic") -> list[str]:
        per_workflow = os.getenv(f"AI_ORCHESTRATOR_PROVIDER_{workflow.upper()}", "").strip()
        raw = per_workflow or os.getenv("AI_ORCHESTRATOR_PROVIDER_ORDER", "local,openai,nvidia")
        ordered = [item.strip().lower() for item in raw.split(",") if item.strip()]
        return [item for item in ordered if item in self.providers] or ["local", "openai", "nvidia"]

    def _provider_snapshot(self, provider_name: str) -> dict[str, Any]:
        provider = self.providers[provider_name]
        try:
            snapshot = provider.describe()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Provider describe failed | provider=%s error=%s", provider_name, exc)
            snapshot = {
                "name": provider_name,
                "available": False,
                "availability_reason": f"describe_failed:{exc}",
                "capabilities": provider.capabilities(),
            }
        snapshot.setdefault("name", provider_name)
        snapshot.setdefault("available", False)
        return snapshot

    async def generate_json(
        self,
        *,
        workflow: str,
        prompt: str,
        system_prompt: str = "",
        task: str = "generic",
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        memory: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
        provider_preferences: list[str] | None = None,
        route_hints: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        require_structured_output: bool = True,
        require_streaming: bool = False,
        allow_fallback: bool = True,
        user_id: str = "",
    ) -> dict[str, Any]:
        if self._uses_runtime():
            response = await self.runtime.execute(
                RuntimeProviderRequest.from_legacy(
                    task=task,
                    workflow=workflow,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    metadata=metadata,
                    conversation_history=conversation_history,
                    memory=memory,
                    rag_context=rag_context,
                    provider_preferences=provider_preferences,
                    route_hints=route_hints,
                    timeout_seconds=timeout_seconds,
                    require_structured_output=require_structured_output,
                    require_streaming=require_streaming,
                    allow_fallback=allow_fallback,
                    user_id=user_id,
                )
            )
            return response.as_legacy_result()

        attempts: list[dict[str, Any]] = []
        for provider_name in self.provider_order(workflow):
            provider = self.providers[provider_name]
            provider_snapshot = self._provider_snapshot(provider_name)
            if not provider_snapshot.get("available"):
                attempts.append(self._legacy_attempt(provider=provider_name, status="unavailable", error=str(provider_snapshot.get("availability_reason") or "provider_unavailable")))
                continue
            attempt_started = time.perf_counter()
            try:
                payload = await provider.generate_json(
                    prompt,
                    system_prompt=system_prompt,
                    workflow=workflow,
                )
            except Exception as exc:  # pragma: no cover - network/provider guard
                latency_ms = round((time.perf_counter() - attempt_started) * 1000, 2)
                logger.warning(
                    "Model provider failed | workflow=%s provider=%s error=%s",
                    workflow,
                    provider_name,
                    exc,
                )
                attempts.append(self._legacy_attempt(provider=provider_name, status="failed", error=str(exc)))
                continue
            latency_ms = round((time.perf_counter() - attempt_started) * 1000, 2)
            if payload:
                attempts.append(self._legacy_attempt(provider=provider_name, status="ready", error=None))
                logger.info(
                    "Model provider selected | workflow=%s provider=%s attempts=%s",
                    workflow,
                    provider_name,
                    attempts,
                )
                return {
                    "provider": provider_name,
                    "payload": payload,
                    "attempts": attempts,
                }
            attempts.append(
                self._legacy_attempt(provider=provider_name, status="empty", error=None)
            )

        logger.warning("Model providers exhausted | workflow=%s attempts=%s", workflow, attempts)
        return {
            "provider": "deterministic_fallback",
            "payload": None,
            "attempts": attempts,
        }

    def health_snapshot(self) -> dict[str, Any]:
        if self._uses_runtime():
            return {
                "provider_order": self.provider_order(),
                "provider_runtime": True,
                "providers": [{"name": name, "available": True} for name in sorted(self.runtime.registry.providers)],
            }
        provider_registry = {
            provider_name: self._provider_snapshot(provider_name)
            for provider_name in self.providers
        }
        return {
            "provider_order": self.provider_order(),
            "providers": list(provider_registry.values()),
            "provider_registry": provider_registry,
        }

    def _legacy_attempt(self, *, provider: str, status: str, error: str | None) -> dict[str, Any]:
        return {
            "provider": provider,
            "status": status,
            "error": error,
        }

    def _uses_runtime(self) -> bool:
        if set(self._providers) != set(self._default_provider_classes):
            return False
        return all(
            self._providers[name].__class__ is self._default_provider_classes[name]
            for name in self._default_provider_classes
        )
