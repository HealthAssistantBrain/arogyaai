from __future__ import annotations

from typing import Any

from pipelines.rag_pipeline.config import RagSettings
from services.ollama_client import get_ollama_availability, get_cached_ollama_health, ollama_generate_json, ollama_provider_enabled

from .base import BaseAIProvider, extract_json_object


class LocalOllamaProvider(BaseAIProvider):
    name = "local"

    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def is_available(self) -> bool:
        return bool(get_ollama_availability(self.settings)["routable"])

    def capabilities(self) -> dict[str, Any]:
        return {
            **super().capabilities(),
            "health_probe": "cached_optional",
            "provider_type": "ollama",
        }

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        workflow: str = "generic",
    ) -> dict[str, Any] | None:
        if not self.is_available():
            return None

        result = await ollama_generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            settings=self.settings,
            model_name=self.settings.ollama_model,
            workflow=workflow,
            options={"temperature": 0.1},
        )
        return extract_json_object(result.get("payload"))

    def describe(self) -> dict[str, Any]:
        cached_probe = get_cached_ollama_health(self.settings) or {}
        availability = get_ollama_availability(self.settings)
        return {
            **super().describe(),
            "enabled": ollama_provider_enabled(),
            "model": self.settings.ollama_model,
            "base_url": self.settings.ollama_base_url,
            "timeout_seconds": self.settings.ollama_timeout_seconds,
            "keep_alive": self.settings.ollama_keep_alive,
            "probe_status": cached_probe.get("status"),
            "probe_cache_hit": cached_probe.get("cache_hit"),
            "availability_reason": availability.get("reason"),
            "routable": availability.get("routable"),
        }
