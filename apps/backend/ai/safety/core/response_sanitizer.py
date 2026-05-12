from __future__ import annotations

from typing import Any, Callable


class ResponseSanitizer:
    def collect_text(self, payload: dict[str, Any], *, policy: dict[str, Any]) -> str:
        chunks: list[str] = []
        self._collect(payload, chunks, policy=policy, path=())
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    def transform_payload(
        self,
        payload: dict[str, Any],
        *,
        policy: dict[str, Any],
        text_transform: Callable[[str, tuple[str, ...]], str],
    ) -> dict[str, Any]:
        return self._transform(payload, policy=policy, path=(), text_transform=text_transform)

    def _collect(self, value: Any, chunks: list[str], *, policy: dict[str, Any], path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in policy.get("raw_text_fields", ()):
                    continue
                next_path = (*path, str(key))
                if isinstance(item, str) and key in policy.get("text_fields", ()):
                    text = item.strip()
                    if text:
                        chunks.append(text)
                elif isinstance(item, list) and key in policy.get("list_fields", ()):
                    for entry in item:
                        if isinstance(entry, str) and entry.strip():
                            chunks.append(entry.strip())
                elif isinstance(item, (dict, list)) and (key in policy.get("recursive_fields", ()) or not path):
                    self._collect(item, chunks, policy=policy, path=next_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._collect(item, chunks, policy=policy, path=(*path, str(index)))

    def _transform(
        self,
        value: Any,
        *,
        policy: dict[str, Any],
        path: tuple[str, ...],
        text_transform: Callable[[str, tuple[str, ...]], str],
    ) -> Any:
        if isinstance(value, dict):
            updated: dict[str, Any] = {}
            for key, item in value.items():
                next_path = (*path, str(key))
                if key in policy.get("raw_text_fields", ()):
                    updated[key] = item
                elif isinstance(item, str) and key in policy.get("text_fields", ()):
                    updated[key] = text_transform(item, next_path)
                elif isinstance(item, list) and key in policy.get("list_fields", ()):
                    updated[key] = [
                        text_transform(entry, (*next_path, str(index))) if isinstance(entry, str) else entry
                        for index, entry in enumerate(item)
                    ]
                elif isinstance(item, (dict, list)) and (key in policy.get("recursive_fields", ()) or not path):
                    updated[key] = self._transform(item, policy=policy, path=next_path, text_transform=text_transform)
                else:
                    updated[key] = item
            return updated
        if isinstance(value, list):
            return [
                self._transform(item, policy=policy, path=(*path, str(index)), text_transform=text_transform)
                if isinstance(item, (dict, list))
                else item
                for index, item in enumerate(value)
            ]
        return value
