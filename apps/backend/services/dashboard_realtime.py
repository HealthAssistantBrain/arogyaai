from __future__ import annotations

import asyncio
import json
import logging
import os
import select
import threading
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2 import extensions
from fastapi import WebSocket
from sqlalchemy.orm import Session

from core.config import settings
from database.session import SessionLocal, engine
from models import User
from services.google_fit_service import GoogleFitService
from services import dashboard_service as dashboard_svc
from services.user_data_service import UserDataService

logger = logging.getLogger("dashboard_realtime")


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _latest_iso(*values: Any) -> str | None:
    candidates = [parsed for parsed in (_parse_iso_datetime(value) for value in values) if parsed is not None]
    if not candidates:
        return None
    return max(candidates).astimezone(timezone.utc).isoformat()


def _slice_last_updated(slice_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(slice_payload, dict):
        return None
    if slice_payload.get("last_updated"):
        return _latest_iso(slice_payload.get("last_updated"))
    data = slice_payload.get("data")
    if isinstance(data, list) and data:
        last_item = data[-1]
        if isinstance(last_item, dict):
            return _latest_iso(last_item.get("timestamp"))
    if isinstance(data, dict):
        return _latest_iso(data.get("last_synced_at"), data.get("last_updated"))
    return None


def _dashboard_last_updated(payload: dict[str, Any]) -> str | None:
    if not isinstance(payload, dict):
        return None

    candidates = [
        _slice_last_updated(payload.get("healthScore")),
        _slice_last_updated(payload.get("history")),
        _slice_last_updated(payload.get("prediction")),
        _slice_last_updated(payload.get("profile")),
        _slice_last_updated(payload.get("alerts")),
        _slice_last_updated(payload.get("googleFit")),
    ]

    vitals = payload.get("vitals")
    if isinstance(vitals, dict):
        for slice_payload in vitals.values():
            candidates.append(_slice_last_updated(slice_payload))

    candidates.append(_latest_iso(payload.get("last_updated")))
    return _latest_iso(*candidates)


def _serialize_vitals_slice(db: Session, current_user: User, vital_type: str, range_value: str = "24h") -> dict[str, Any]:
    payload = UserDataService.list_vitals(db, current_user, vital_type=vital_type, range_value=range_value)
    vitals = payload.get("data", {}).get("vitals", []) if isinstance(payload, dict) else []
    trimmed = vitals[-100:] if len(vitals) > 100 else vitals
    return {
        "type": vital_type,
        "range": range_value,
        "data": trimmed,
        "total_count": len(trimmed),
        "last_updated": payload.get("last_updated") if isinstance(payload, dict) else None,
        "missing": [],
        "status": "ready" if trimmed else "fallback",
        "source": "db",
    }


async def build_dashboard_bundle(db: Session, current_user: User) -> dict[str, Any]:
    health_score = await dashboard_svc.get_health_score(current_user, db)
    history = await dashboard_svc.get_health_history(current_user, db)
    prediction = await dashboard_svc.get_latest_prediction(current_user, db)
    profile = await dashboard_svc.get_user_profile(current_user, db)
    alerts = await dashboard_svc.get_alerts(current_user, db)
    google_fit = {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": GoogleFitService.get_status(db, current_user),
    }

    bundle = {
        "healthScore": health_score,
        "history": history,
        "prediction": prediction,
        "profile": profile,
        "alerts": alerts,
        "googleFit": google_fit,
        "vitals": {
            "heart_rate:24h": _serialize_vitals_slice(db, current_user, "heart_rate", "24h"),
            "steps:24h": _serialize_vitals_slice(db, current_user, "steps", "24h"),
            "sleep:24h": _serialize_vitals_slice(db, current_user, "sleep", "24h"),
        },
    }
    bundle["last_updated"] = _dashboard_last_updated(bundle)
    return bundle


async def build_realtime_payload(db: Session, current_user: User) -> dict[str, Any]:
    heart_rate = _serialize_vitals_slice(db, current_user, "heart_rate", "24h")
    steps = _serialize_vitals_slice(db, current_user, "steps", "24h")
    google_fit_status = GoogleFitService.get_status(db, current_user)
    google_fit = {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": google_fit_status,
        "last_updated": google_fit_status.get("last_synced_at"),
    }
    payload = {
        "steps": steps,
        "heart_rate": heart_rate,
        "googleFit": google_fit,
    }
    payload["last_updated"] = _dashboard_last_updated(payload)
    return payload


def _build_psycopg2_kwargs() -> dict[str, Any]:
    url = engine.url
    kwargs: dict[str, Any] = {}
    if url.database:
        kwargs["dbname"] = url.database
    if url.username:
        kwargs["user"] = url.username
    if url.password:
        kwargs["password"] = url.password
    if url.host:
        kwargs["host"] = url.host
    if url.port:
        kwargs["port"] = url.port
    kwargs["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3"))
    if url.query.get("sslmode"):
        kwargs["sslmode"] = url.query["sslmode"]
    return kwargs


class DashboardConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            sockets = self._connections.setdefault(user_id, [])
            if websocket not in sockets:
                sockets.append(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return
            sockets = [socket for socket in sockets if socket is not websocket]
            if sockets:
                self._connections[user_id] = sockets
                return
            self._connections.pop(user_id, None)

    async def broadcast(self, user_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(user_id, []))

        if not sockets:
            return

        message = json.dumps(payload)
        dead_sockets: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_sockets.append(websocket)

        if dead_sockets:
            async with self._lock:
                sockets = self._connections.get(user_id)
                if sockets:
                    for websocket in dead_sockets:
                        sockets = [socket for socket in sockets if socket is not websocket]
                    if sockets:
                        self._connections[user_id] = sockets
                    else:
                        self._connections.pop(user_id, None)


dashboard_connection_manager = DashboardConnectionManager()

_listener_thread: threading.Thread | None = None
_listener_stop = threading.Event()
_listener_loop: asyncio.AbstractEventLoop | None = None
_pending_user_tasks: dict[str, asyncio.Task] = {}


async def _broadcast_current_snapshot(user_id: str) -> None:
    db = SessionLocal()
    try:
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return

        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if not user:
            return

        payload = await build_realtime_payload(db, user)
        await dashboard_connection_manager.broadcast(
            str(user.id),
            {
                "type": "dashboard.update",
                "user_id": str(user.id),
                "data": payload,
                "last_updated": payload.get("last_updated"),
            },
        )
    finally:
        db.close()


def _schedule_broadcast(user_id: str) -> None:
    if user_id in _pending_user_tasks:
        return

    async def _runner() -> None:
        try:
            await asyncio.sleep(0.25)
            await _broadcast_current_snapshot(user_id)
        finally:
            _pending_user_tasks.pop(user_id, None)

    _pending_user_tasks[user_id] = asyncio.create_task(_runner())


def _enqueue_broadcast(user_id: str) -> None:
    loop = _listener_loop
    if not loop or loop.is_closed():
        return
    loop.call_soon_threadsafe(_schedule_broadcast, user_id)


def _listen_for_dashboard_updates() -> None:
    kwargs = _build_psycopg2_kwargs()
    while not _listener_stop.is_set():
        conn = None
        try:
            conn = psycopg2.connect(**kwargs)
            conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute("LISTEN dashboard_updates;")
            logger.info("[Dashboard WS] LISTEN dashboard_updates active")

            while not _listener_stop.is_set():
                if select.select([conn], [], [], 1) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    notification = conn.notifies.pop(0)
                    try:
                        payload = json.loads(notification.payload or "{}")
                    except Exception:
                        logger.warning("[Dashboard WS] Ignoring malformed notification payload")
                        continue
                    user_id = str(payload.get("user_id") or "").strip()
                    if not user_id:
                        continue
                    _enqueue_broadcast(user_id)
        except Exception as exc:
            if not _listener_stop.is_set():
                logger.warning("[Dashboard WS] Listener error: %s", exc)
                time.sleep(2)
        finally:
            if conn is not None:
                with suppress(Exception):
                    conn.close()


def start_dashboard_realtime_listener(loop: asyncio.AbstractEventLoop) -> None:
    global _listener_thread, _listener_loop
    if _listener_thread and _listener_thread.is_alive():
        _listener_loop = loop
        return

    _listener_stop.clear()
    _listener_loop = loop
    _listener_thread = threading.Thread(target=_listen_for_dashboard_updates, name="dashboard-realtime-listener", daemon=True)
    _listener_thread.start()
    logger.info("[Dashboard WS] Realtime listener started")


def stop_dashboard_realtime_listener() -> None:
    global _listener_thread, _listener_loop
    _listener_stop.set()
    thread = _listener_thread
    if thread and thread.is_alive():
        thread.join(timeout=3)
    _listener_thread = None
    _listener_loop = None
