from __future__ import annotations

from typing import Any


class DialoguePruning:
    def prune_history(self, history: list[dict[str, Any]] | None, *, limit: int = 8) -> list[dict[str, str]]:
        pruned: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in history or []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            normalized = " ".join(content.split())
            key = (role, normalized.lower())
            if key in seen:
                continue
            seen.add(key)
            pruned.append({"role": role, "content": normalized[:280]})
        return pruned[-limit:]

    def unique_texts(self, values: list[Any] | None, *, limit: int = 4) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for value in values or []:
            if isinstance(value, dict):
                text = str(
                    value.get("summary")
                    or value.get("content")
                    or value.get("title")
                    or value.get("detail")
                    or ""
                ).strip()
            else:
                text = str(value or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            items.append(text)
            if len(items) >= limit:
                break
        return items
