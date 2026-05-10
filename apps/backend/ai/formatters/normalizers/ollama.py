from __future__ import annotations

from typing import Any

from .base import ProviderResponseNormalizer


class OllamaResponseNormalizer(ProviderResponseNormalizer):
    provider_name = "ollama"

    def _candidate_values(self, raw_response: Any) -> list[Any]:
        values = super()._candidate_values(raw_response)
        if isinstance(raw_response, dict):
            message = raw_response.get("message")
            if isinstance(message, dict):
                values.extend([message, message.get("content")])
            values.extend([raw_response.get("response"), raw_response.get("output")])
        return values
