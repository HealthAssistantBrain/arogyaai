from __future__ import annotations

import os
import threading
import time
from hashlib import sha256
from typing import Any


class ResponseCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}
        self.ttl_seconds = max(5.0, float(os.getenv("AI_PROVIDER_CACHE_TTL_SECONDS", "600")))

    def _key(self, *, task: str, workflow: str, prompt: str, context: dict[str, Any]) -> str:
        material = f"{task}|{workflow}|{prompt}|{context}".encode("utf-8", errors="ignore")
        return sha256(material).hexdigest()

    def get(self, *, task: str, workflow: str, prompt: str, context: dict[str, Any]) -> dict[str, Any] | None:
        key = self._key(task=task, workflow=workflow, prompt=prompt, context=context)
        now = time.monotonic()
        with self._lock:
            cached = self._items.get(key)
            if cached is None:
                return None
            expires_at, payload = cached
            if now >= expires_at:
                self._items.pop(key, None)
                return None
            return dict(payload)

    def set(self, *, task: str, workflow: str, prompt: str, context: dict[str, Any], payload: dict[str, Any]) -> None:
        key = self._key(task=task, workflow=workflow, prompt=prompt, context=context)
        with self._lock:
            self._items[key] = (time.monotonic() + self.ttl_seconds, dict(payload))
