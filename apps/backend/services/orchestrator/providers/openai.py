from __future__ import annotations

from typing import Any

import httpx

from pipelines.rag_pipeline.config import RagSettings

from .base import BaseAIProvider, extract_json_object


class OpenAICompatibleProvider(BaseAIProvider):
    name = "openai"

    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def is_available(self) -> bool:
        return bool(self.settings.llm_api_base and self.settings.llm_api_key and self.settings.llm_api_model)

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        workflow: str = "generic",
    ) -> dict[str, Any] | None:
        if not self.is_available():
            return None

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.llm_api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_api_model,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                            or "You are ArogyaAI's clinical orchestration model. Return JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            return None
        message = (choices[0].get("message") or {}).get("content") or ""
        return extract_json_object(message)

    def describe(self) -> dict[str, Any]:
        return {
            **super().describe(),
            "model": self.settings.llm_api_model,
            "base_url": self.settings.llm_api_base,
        }
