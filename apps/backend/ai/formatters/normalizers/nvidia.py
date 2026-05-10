from __future__ import annotations

from typing import Any

from .base import ProviderResponseNormalizer


class NvidiaResponseNormalizer(ProviderResponseNormalizer):
    provider_name = "nvidia"

    def _candidate_values(self, raw_response: Any) -> list[Any]:
        values = super()._candidate_values(raw_response)
        if isinstance(raw_response, dict):
            values.extend(
                [
                    raw_response.get("completion"),
                    raw_response.get("response"),
                    ((raw_response.get("choices") or [{}])[0] if isinstance(raw_response.get("choices"), list) else {}),
                ]
            )
        return values
