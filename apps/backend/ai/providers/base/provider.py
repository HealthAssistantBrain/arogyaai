from __future__ import annotations

import abc
from typing import Any, AsyncIterator

from ..models.payloads import ProviderRequest


class BaseProvider(abc.ABC):
    name = "base"
    optional = True

    @abc.abstractmethod
    async def generate(self, request: ProviderRequest, *, model: str) -> dict[str, Any]:
        raise NotImplementedError

    async def stream_generate(self, request: ProviderRequest, *, model: str) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError(f"{self.name} does not support streaming")

    async def embeddings(self, inputs: list[str], *, model: str | None = None) -> list[list[float]]:
        raise NotImplementedError(f"{self.name} does not support embeddings")

    async def summarize(self, request: ProviderRequest, *, model: str) -> dict[str, Any]:
        return await self.generate(request, model=model)

    async def structured_generate(self, request: ProviderRequest, *, model: str) -> dict[str, Any]:
        return await self.generate(request, model=model)

    @abc.abstractmethod
    async def healthcheck(self) -> dict[str, Any]:
        raise NotImplementedError

    async def available_models(self) -> list[str]:
        return []

    def validate_response(self, response: Any) -> bool:
        return response is not None

    def token_estimate(self, value: Any) -> int:
        return max(1, len(str(value or "")) // 4)

    def supports_streaming(self) -> bool:
        return False

    def supports_json_mode(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        return False
