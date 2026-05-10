from __future__ import annotations

from typing import Any

from .base import ProviderResponseNormalizer


class OpenAICompatibleResponseNormalizer(ProviderResponseNormalizer):
    provider_name = "openai_compatible"

    def _candidate_values(self, raw_response: Any) -> list[Any]:
        values = super()._candidate_values(raw_response)
        if isinstance(raw_response, dict) and isinstance(raw_response.get("choices"), list):
            for choice in raw_response.get("choices") or []:
                if not isinstance(choice, dict):
                    continue
                values.append(choice)
                message = choice.get("message")
                if isinstance(message, dict):
                    values.extend([message, message.get("content")])
        return values
