from __future__ import annotations

import abc
import json
from typing import Any


class BaseAIProvider(abc.ABC):
    name = "base"
    optional = True

    @abc.abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        workflow: str = "generic",
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    def capabilities(self) -> dict[str, Any]:
        return {
            "structured_json": True,
            "optional": self.optional,
        }

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.is_available(),
            "capabilities": self.capabilities(),
        }


def extract_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
