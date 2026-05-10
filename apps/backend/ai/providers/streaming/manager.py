from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ..models.payloads import ProviderResponse


class StreamingManager:
    async def finalize(self, chunks: AsyncIterator[dict[str, Any]]) -> ProviderResponse | None:
        aggregated: dict[str, Any] = {"text": "", "content": {}, "cadence": []}
        async for chunk in chunks:
            token = str(chunk.get("delta") or chunk.get("text") or "").strip()
            if token:
                aggregated["text"] += token + " "
                aggregated["cadence"].append(
                    {
                        "size": len(token.split()),
                        "type": "sentence" if token.endswith((".", "!", "?")) else "phrase",
                    }
                )
            if isinstance(chunk.get("content"), dict):
                aggregated["content"].update(chunk["content"])
        return None if not aggregated["text"] and not aggregated["content"] else aggregated
