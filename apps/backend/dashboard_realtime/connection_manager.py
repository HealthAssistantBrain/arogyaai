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

from core.serialization.safe_response import is_socket_alive, websocket_send_json_safe

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
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    tasks: set[asyncio.Task[Any]] = field(default_factory=set)


class DashboardConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, _ConnectionRecord] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        stale_record: _ConnectionRecord | None = None
        reconnect_count = 0

        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is not None:
                reconnect_count = existing.reconnect_count + 1
                stale_record = existing
            self._connections[user_id] = _ConnectionRecord(
                websocket=websocket,
                session_id=session_id,
                reconnect_count=reconnect_count,
            )

        logger.info("[WS CONNECT] user_id=%s session_id=%s reconnect_count=%s", user_id, session_id, reconnect_count)

        if stale_record is not None and stale_record.websocket is not websocket:
            await self._cleanup_record(
                user_id,
                stale_record,
                reason="superseded",
                close_code=4001,
                close_reason="superseded",
                emit_disconnect=False,
            )
        return session_id

    async def disconnect(
        self,
        user_id: str,
        websocket: WebSocket,
        *,
        session_id: str | None = None,
        reason: str = "disconnect",
    ) -> None:
        record: _ConnectionRecord | None = None
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return
            if existing.websocket is not websocket:
                return
            if session_id is not None and existing.session_id != session_id:
                return
            record = self._connections.pop(user_id, None)

        if record is not None:
            await self._cleanup_record(user_id, record, reason=reason, emit_disconnect=True)

    async def has_connection(self, user_id: str) -> bool:
        async with self._lock:
            return user_id in self._connections

    async def mark_heartbeat(self, user_id: str, websocket: WebSocket, *, session_id: str | None = None) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None or existing.websocket is not websocket:
                return
            if session_id is not None and existing.session_id != session_id:
                return
            existing.last_heartbeat = time.monotonic()
            logger.debug("[WS HEARTBEAT] user_id=%s session_id=%s", user_id, existing.session_id)

    async def prime_snapshot(self, user_id: str, payload: dict[str, Any], *, session_id: str | None = None) -> None:
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return
            if session_id is not None and existing.session_id != session_id:
                return
            existing.last_payload = copy.deepcopy(payload)

    async def register_task(
        self,
        user_id: str,
        task: asyncio.Task[Any],
        *,
        session_id: str | None = None,
    ) -> bool:
        should_cancel = False
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                should_cancel = True
            elif session_id is not None and existing.session_id != session_id:
                should_cancel = True
            else:
                existing.tasks.add(task)

        if should_cancel:
            task.cancel()
            return False

        def _cleanup(done_task: asyncio.Task[Any]) -> None:
            async def _discard() -> None:
                async with self._lock:
                    current = self._connections.get(user_id)
                    if current is not None:
                        current.tasks.discard(done_task)

            asyncio.create_task(_discard())

        task.add_done_callback(_cleanup)
        return True

    async def cancel_tasks(self, user_id: str, *, session_id: str | None = None, reason: str = "cleanup") -> int:
        tasks: set[asyncio.Task[Any]] = set()
        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return 0
            if session_id is not None and existing.session_id != session_id:
                return 0
            tasks = set(existing.tasks)
            existing.tasks.clear()

        for task in tasks:
            task.cancel()
        if tasks:
            logger.info("[WS CLEANUP] user_id=%s session_id=%s action=cancel_tasks count=%s reason=%s", user_id, session_id, len(tasks), reason)
        return len(tasks)

    async def broadcast_snapshot(self, user_id: str, payload: dict[str, Any]) -> None:
        record, previous = await self._prepare_active_record(user_id, update_payload=payload)
        if record is None:
            return

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
        await self._send_on_record(user_id, record, message, context=message_type)

    async def broadcast(self, user_id: str, payload: dict[str, Any]) -> None:
        if isinstance(payload, dict) and str(payload.get("type") or "").startswith("dashboard.") and isinstance(payload.get("data"), dict):
            meta = payload.get("meta")
            if isinstance(meta, dict) and meta.get("degraded"):
                record, _previous = await self._prepare_active_record(user_id)
                if record is None:
                    return
                await self._send_on_record(user_id, record, payload, context=str(payload.get("type") or "dashboard.degraded"))
                return
            await self.broadcast_snapshot(user_id, payload["data"])
            return
        await self.broadcast_snapshot(user_id, payload if isinstance(payload, dict) else {"payload": payload})

    async def _prepare_active_record(
        self,
        user_id: str,
        *,
        update_payload: dict[str, Any] | None = None,
    ) -> tuple[_ConnectionRecord | None, dict[str, Any] | None]:
        stale_record: _ConnectionRecord | None = None
        previous: dict[str, Any] | None = None

        async with self._lock:
            existing = self._connections.get(user_id)
            if existing is None:
                return None, None
            if time.monotonic() - existing.last_heartbeat > HEARTBEAT_TTL_SECONDS:
                stale_record = self._connections.pop(user_id, None)
            else:
                previous = copy.deepcopy(existing.last_payload) if existing.last_payload else None
                if update_payload is not None:
                    existing.last_payload = copy.deepcopy(update_payload)
                return existing, previous

        if stale_record is not None:
            await self._cleanup_record(
                user_id,
                stale_record,
                reason="heartbeat_timeout",
                close_code=4002,
                close_reason="heartbeat_timeout",
                emit_disconnect=True,
            )
        return None, None

    async def _send_on_record(
        self,
        user_id: str,
        record: _ConnectionRecord,
        payload: dict[str, Any],
        *,
        context: str,
    ) -> None:
        async with record.send_lock:
            async with self._lock:
                current = self._connections.get(user_id)
                if current is None or current.session_id != record.session_id or current.websocket is not record.websocket:
                    logger.info("[WS CLOSED] action=skip_superseded user_id=%s session_id=%s context=%s", user_id, record.session_id, context)
                    return

            if not is_socket_alive(record.websocket):
                await self._remove_dead_socket(user_id, record, reason="socket_not_alive")
                return

            sent = await websocket_send_json_safe(
                record.websocket,
                payload,
                channel="dashboard.broadcast",
                context=f"{context}:{user_id}:{record.session_id}",
            )
            if not sent:
                await self._remove_dead_socket(user_id, record, reason="send_failed")
                return

            logger.info(
                "[WS BROADCAST] user_id=%s session_id=%s type=%s changed_keys=%s",
                user_id,
                record.session_id,
                payload.get("type"),
                ((payload.get("meta") or {}).get("changed_keys") if isinstance(payload.get("meta"), dict) else None),
            )

    async def _remove_dead_socket(self, user_id: str, record: _ConnectionRecord, *, reason: str) -> None:
        removed: _ConnectionRecord | None = None
        async with self._lock:
            current = self._connections.get(user_id)
            if current is None:
                return
            if current.session_id != record.session_id or current.websocket is not record.websocket:
                return
            removed = self._connections.pop(user_id, None)

        if removed is not None:
            await self._cleanup_record(user_id, removed, reason=reason, emit_disconnect=True)
            logger.info("[WS DEAD SOCKET REMOVED] user_id=%s session_id=%s reason=%s", user_id, removed.session_id, reason)

    async def _cleanup_record(
        self,
        user_id: str,
        record: _ConnectionRecord,
        *,
        reason: str,
        close_code: int | None = None,
        close_reason: str | None = None,
        emit_disconnect: bool,
    ) -> None:
        tasks = list(record.tasks)
        record.tasks.clear()
        for task in tasks:
            task.cancel()

        if emit_disconnect:
            logger.info("[WS DISCONNECT] user_id=%s session_id=%s reason=%s", user_id, record.session_id, reason)
        logger.info("[WS CLEANUP] user_id=%s session_id=%s cancelled_tasks=%s reason=%s", user_id, record.session_id, len(tasks), reason)

        if close_code is not None and is_socket_alive(record.websocket):
            try:
                await record.websocket.close(code=close_code, reason=close_reason)
            except Exception:
                logger.debug("[WS CLEANUP] close failed", exc_info=True)


dashboard_connection_manager = DashboardConnectionManager()
