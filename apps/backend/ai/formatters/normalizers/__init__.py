from __future__ import annotations

from .base import NormalizedOutput, ProviderResponseNormalizer
from .nvidia import NvidiaResponseNormalizer
from .ollama import OllamaResponseNormalizer
from .openai_compatible import OpenAICompatibleResponseNormalizer


def get_provider_normalizer(provider: str | None) -> ProviderResponseNormalizer:
    normalized = str(provider or "").strip().lower()
    if normalized == "nvidia":
        return NvidiaResponseNormalizer()
    if normalized in {"ollama", "local"}:
        return OllamaResponseNormalizer()
    if normalized in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleResponseNormalizer()
    return ProviderResponseNormalizer()


__all__ = [
    "NormalizedOutput",
    "OpenAICompatibleResponseNormalizer",
    "OllamaResponseNormalizer",
    "ProviderResponseNormalizer",
    "NvidiaResponseNormalizer",
    "get_provider_normalizer",
]
