from __future__ import annotations

from pipelines.rag_pipeline.config import RagSettings

from ..adapters.nvidia import NvidiaProviderAdapter
from ..adapters.ollama import OllamaProviderAdapter
from ..adapters.openai_compatible import OpenAICompatibleProviderAdapter


class ProviderRegistry:
    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or RagSettings()
        self.providers = {
            "nvidia": NvidiaProviderAdapter(self.settings),
            "ollama": OllamaProviderAdapter(self.settings),
            "openai": OpenAICompatibleProviderAdapter(self.settings),
        }

    def available_provider_names(self) -> set[str]:
        return set(self.providers)

    def available_models(self) -> dict[str, list[str]]:
        payload: dict[str, list[str]] = {}
        for name, provider in self.providers.items():
            try:
                payload[name] = list(provider.static_models())
            except Exception:
                payload[name] = []
        return payload
