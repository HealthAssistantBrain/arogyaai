from __future__ import annotations

import os
import logging
from dataclasses import asdict, dataclass
from typing import Any

from pipelines.rag_pipeline.config import RagSettings

from .providers.base import BaseAIProvider
from .providers.local import LocalOllamaProvider
from .providers.nvidia import NvidiaProvider
from .providers.openai import OpenAICompatibleProvider

logger = logging.getLogger("uvicorn.error")


@dataclass(slots=True)
class ProviderAttempt:
    provider: str
    status: str
    error: str | None = None


class ModelRegistry:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.providers: dict[str, BaseAIProvider] = {
            "local": LocalOllamaProvider(self.settings),
            "openai": OpenAICompatibleProvider(self.settings),
            "nvidia": NvidiaProvider(),
        }

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
    ) -> dict[str, Any]:
        attempts: list[dict[str, Any]] = []
        for provider_name in self.provider_order(workflow):
            provider = self.providers[provider_name]
            provider_snapshot = self._provider_snapshot(provider_name)
            if not provider_snapshot.get("available"):
                attempts.append(
                    asdict(
                        ProviderAttempt(
                            provider=provider_name,
                            status="unavailable",
                            error=str(provider_snapshot.get("availability_reason") or "provider_unavailable"),
                        )
                    )
                )
                continue
            try:
                payload = await provider.generate_json(
                    prompt,
                    system_prompt=system_prompt,
                    workflow=workflow,
                )
            except Exception as exc:  # pragma: no cover - network/provider guard
                logger.warning(
                    "Model provider failed | workflow=%s provider=%s error=%s",
                    workflow,
                    provider_name,
                    exc,
                )
                attempts.append(asdict(ProviderAttempt(provider=provider_name, status="failed", error=str(exc))))
                continue
            if payload:
                attempts.append(asdict(ProviderAttempt(provider=provider_name, status="ready")))
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
            attempts.append(asdict(ProviderAttempt(provider=provider_name, status="empty")))

        logger.warning("Model providers exhausted | workflow=%s attempts=%s", workflow, attempts)
        return {
            "provider": "deterministic_fallback",
            "payload": None,
            "attempts": attempts,
        }

    def health_snapshot(self) -> dict[str, Any]:
        provider_registry = {
            provider_name: self._provider_snapshot(provider_name)
            for provider_name in self.providers
        }
        return {
            "provider_order": self.provider_order(),
            "providers": list(provider_registry.values()),
            "provider_registry": provider_registry,
        }
