from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from core.serialization import safe_json_dumps

logger = logging.getLogger("dashboard_connection_manager")
HEARTBEAT_TTL_SECONDS = 70.0


def _json_fingerprint(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except Exception:
        return str(value)


def _top_level_patch(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return copy.deepcopy(current)
    changed: dict[str, Any] = {}
    for key, value in current.items():
        if _json_fingerprint(previous.get(key)) != _json_fingerprint(value):
            changed[key] = copy.deepcopy(value)
    return changed


@dataclass
class _ConnectionRecord:
    websocket: WebSocket
    session_id: str
    connected_at: float = field(default_factory=time.monotonic)
    last_heartbeat: float = field(default_factory=time.monotonic)
    reconnect_count: int = 0
    last_payload: dict[str, Any] | None = None


class DashboardConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, _ConnectionRecord] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        stale_socket: WebSocket | None = None
        reconnect_count = 0
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is not None:
                reconnect_count = existing.reconnect_count + 1
                stale_socket = existing.websocket
            self._connections[user_id] = _ConnectionRecord(
                websocket=websocket,
                session_id=session_id,
                reconnect_count=reconnect_count,
            )

        if stale_socket is not None and stale_socket is not websocket:
            logger.warning("[WS STALE SOCKET] user=%s action=close_duplicate", user_id)
            try:
                await stale_socket.close(code=4001, reason="superseded")
            except Exception:
                logger.debug("[WS STALE SOCKET] failed to close duplicate", exc_info=True)

        if reconnect_count > 0:
            logger.info("[WS RECONNECT] user=%s reconnect_count=%s", user_id, reconnect_count)
        return session_id

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None or existing.websocket is not websocket:
                return
            self._connections.pop(user_id, None)

    async def mark_heartbeat(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None or existing.websocket is not websocket:
                return
            existing.last_heartbeat = time.monotonic()

    async def prime_snapshot(self, user_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return
            existing.last_payload = copy.deepcopy(payload)

    async def broadcast_snapshot(self, user_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return
            if time.monotonic() - existing.last_heartbeat > HEARTBEAT_TTL_SECONDS:
                websocket = existing.websocket
                self._connections.pop(user_id, None)
                logger.warning("[WS STALE SOCKET] user=%s action=drop_no_heartbeat", user_id)
                try:
                    await websocket.close(code=4002, reason="heartbeat_timeout")
                except Exception:
                    logger.debug("[WS STALE SOCKET] failed to close timed-out socket", exc_info=True)
                return
            previous = copy.deepcopy(existing.last_payload) if existing.last_payload else None
            existing.last_payload = copy.deepcopy(payload)
            websocket = existing.websocket

        patch = _top_level_patch(previous, payload)
        message_type = "dashboard.update" if previous is None or len(patch) == len(payload) else "dashboard.patch"
        message = {
            "type": message_type,
            "user_id": user_id,
            "data": payload if message_type == "dashboard.update" else patch,
            "last_updated": payload.get("last_updated"),
            "meta": {
                "changed_keys": sorted((patch if message_type == "dashboard.patch" else payload).keys()),
                "full_reload": message_type == "dashboard.update",
            },
        }
        if message_type == "dashboard.patch":
            logger.info("[DASHBOARD PATCH UPDATE] user=%s changed_keys=%s", user_id, message["meta"]["changed_keys"])
        try:
            await websocket.send_text(safe_json_dumps(message, channel="dashboard.broadcast"))
        except Exception:
            logger.debug("[WS STALE SOCKET] send failed", exc_info=True)
            await self.disconnect(user_id, websocket)

    async def broadcast(self, user_id: str, payload: dict[str, Any]) -> None:
        if isinstance(payload, dict) and str(payload.get("type") or "").startswith("dashboard.") and isinstance(payload.get("data"), dict):
            meta = payload.get("meta")
            if isinstance(meta, dict) and meta.get("degraded"):
                async with self._lock:
                    existing = self._connections.get(user_id)
                    if existing is None:
                        return
                    websocket = existing.websocket
                try:
                    await websocket.send_text(safe_json_dumps(payload, channel="dashboard.broadcast"))
                except Exception:
                    logger.debug("[WS STALE SOCKET] send failed", exc_info=True)
                    await self.disconnect(user_id, websocket)
                return
            await self.broadcast_snapshot(user_id, payload["data"])
            return
        await self.broadcast_snapshot(user_id, payload if isinstance(payload, dict) else {"payload": payload})


dashboard_connection_manager = DashboardConnectionManager()
