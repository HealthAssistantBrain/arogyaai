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
from uuid import UUID

import psycopg2
from psycopg2 import extensions
from sqlalchemy.orm import Session

from core.config import settings
from core.resilience import TimeoutPolicyError, run_with_timeout
from core.serialization import normalize_outbound_payload
from database.session import SessionLocal, get_listener_engines
from models import User
from dashboard_realtime.connection_manager import DashboardConnectionManager, dashboard_connection_manager
from services.google_fit_service import GoogleFitService
from services import dashboard_service as dashboard_svc
from services.user_data_service import UserDataService

logger = logging.getLogger("dashboard_realtime")
DASHBOARD_AGGREGATION_TIMEOUT_SECONDS = 5.0


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
        _slice_last_updated(payload.get("forecast")),
        _slice_last_updated(payload.get("preventive")),
        _slice_last_updated(payload.get("prediction")),
        _slice_last_updated(payload.get("profile")),
        _slice_last_updated(payload.get("alerts")),
        _slice_last_updated(payload.get("recommendedTests")),
        _slice_last_updated(payload.get("googleFit")),
        _slice_last_updated(payload.get("heart_rate")),
        _slice_last_updated(payload.get("steps")),
        _slice_last_updated(payload.get("sleep")),
    ]

    vitals = payload.get("vitals")
    if isinstance(vitals, dict):
        for slice_payload in vitals.values():
            candidates.append(_slice_last_updated(slice_payload))

    candidates.append(_latest_iso(payload.get("last_updated")))
    return _latest_iso(*candidates)


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_latest_steps(bundle: dict[str, Any]) -> int:
    google_fit = _safe_dict(bundle.get("googleFit"))
    google_fit_data = _safe_dict(google_fit.get("data"))
    stats = _safe_dict(google_fit_data.get("stats"))
    day_payload = _safe_dict(stats.get("latest_day"))
    latest_steps = day_payload.get("steps")
    try:
        return max(0, int(round(float(latest_steps))))
    except (TypeError, ValueError):
        pass

    return 0


def _dashboard_flat_contract(bundle: dict[str, Any]) -> dict[str, Any]:
    history_data = _safe_dict(_safe_dict(bundle.get("history")).get("data"))
    prediction_data = _safe_dict(_safe_dict(bundle.get("prediction")).get("data"))
    forecast_data = _safe_dict(_safe_dict(bundle.get("forecast")).get("data"))
    preventive_data = _safe_dict(_safe_dict(bundle.get("preventive")).get("data"))
    health_score_data = _safe_dict(_safe_dict(bundle.get("healthScore")).get("data"))
    recommended_tests = _safe_list(_safe_dict(bundle.get("recommendedTests")).get("data"))

    sleep_records = _safe_list(history_data.get("sleep"))
    insights = _safe_list(prediction_data.get("recommendations"))
    vitals = _safe_dict(bundle.get("vitals"))

    flat = {**bundle}
    if bundle.get("healthScore") is not None:
        flat["health_score"] = float(health_score_data.get("score") or 0)
    if bundle.get("steps") is None and (bundle.get("googleFit") is not None or bundle.get("vitals") is not None):
        flat["steps"] = _extract_latest_steps(bundle)
    if bundle.get("history") is not None:
        flat["sleep"] = sleep_records
    if bundle.get("prediction") is not None:
        flat["insights"] = insights
    if bundle.get("forecast") is not None:
        flat["forecast"] = forecast_data
    if bundle.get("preventive") is not None:
        flat["prevention"] = preventive_data
    if bundle.get("recommendedTests") is not None:
        flat["recommended_tests"] = recommended_tests
    if bundle.get("vitals") is not None:
        flat["vitals"] = vitals
    return flat


def _normalize_dashboard_payload(payload: dict[str, Any], *, channel: str) -> dict[str, Any]:
    normalized = normalize_outbound_payload(_dashboard_flat_contract(payload), channel=channel)
    return normalized if isinstance(normalized, dict) else {"data": normalized}


def _degraded_dashboard_message(user_id: str, *, reason: str) -> dict[str, Any]:
    last_updated = datetime.now(timezone.utc).isoformat()
    return {
        "type": "dashboard.update",
        "user_id": str(user_id),
        "data": {
            "status": "degraded",
            "error": reason,
            "message": "Realtime dashboard snapshot temporarily sanitized.",
            "last_updated": last_updated,
        },
        "last_updated": last_updated,
        "meta": {
            "degraded": True,
            "reason": reason,
        },
    }


def _serialize_vitals_slice(db: Session, current_user: User, vital_type: str, range_value: str = "24h") -> dict[str, Any]:
    try:
        payload = UserDataService.list_vitals(db, current_user, vital_type=vital_type, range_value=range_value)
    except Exception as e:
        logger.error(f"Error fetching vitals slice {vital_type}: {e}")
        payload = {}
        
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


async def _safe_call(coro, fallback_data=None):
    try:
        return await coro
    except Exception as e:
        logger.error(f"Pipeline component error: {e}")
        return {
            "success": False,
            "status": "fallback",
            "source": "error",
            "error": str(e),
            "data": fallback_data if fallback_data is not None else {}
        }

async def _run_user_slice(
    user_id: str,
    fetcher,
    *,
    fallback_data=None,
):
    session = SessionLocal()
    try:
        user_uuid = UUID(str(user_id))
        fresh_user = session.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if fresh_user is None:
            return {
                "success": False,
                "status": "fallback",
                "source": "db",
                "error": "user_not_found",
                "data": fallback_data if fallback_data is not None else {},
            }
        result = fetcher(session, fresh_user)
        if asyncio.iscoroutine(result):
            return await _safe_call(result, fallback_data=fallback_data)
        return result
    except Exception as exc:
        logger.error("Dashboard slice failed | user_id=%s error=%s", user_id, exc)
        return {
            "success": False,
            "status": "fallback",
            "source": "error",
            "error": str(exc),
            "data": fallback_data if fallback_data is not None else {},
        }
    finally:
        session.close()


async def build_dashboard_bundle(db: Session, current_user: User) -> dict[str, Any]:
    async def _build() -> dict[str, Any]:
        user_id = str(current_user.id)
        (
            health_score,
            history,
            forecast,
            preventive,
            prediction,
            profile,
            alerts,
            recommended_tests,
            google_fit_status,
            vitals,
        ) = await asyncio.gather(
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_health_score(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_health_history(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_health_forecast(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_preventive_intelligence(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_latest_prediction(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_user_profile(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_alerts(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_recommended_tests(user, session), fallback_data=[]),
            _run_user_slice(user_id, lambda session, user: {"success": True, "status": "ready", "source": "db", "error": None, "data": GoogleFitService.get_status(session, user)}),
            _run_user_slice(
                user_id,
                lambda session, user: {
                    "heart_rate:24h": _serialize_vitals_slice(session, user, "heart_rate", "24h"),
                    "steps:24h": _serialize_vitals_slice(session, user, "steps", "24h"),
                    "sleep:24h": _serialize_vitals_slice(session, user, "sleep", "24h"),
                },
            ),
        )

        bundle = {
            "healthScore": health_score,
            "history": history,
            "forecast": forecast,
            "preventive": preventive,
            "prediction": prediction,
            "profile": profile,
            "alerts": alerts,
            "recommendedTests": recommended_tests,
            "googleFit": google_fit_status,
            "vitals": vitals if isinstance(vitals, dict) else {},
        }
        bundle["last_updated"] = _dashboard_last_updated(bundle)
        return _normalize_dashboard_payload(bundle, channel="dashboard.bundle")

    try:
        return await run_with_timeout(
            _build(),
            timeout_seconds=DASHBOARD_AGGREGATION_TIMEOUT_SECONDS,
            operation="dashboard_bundle",
        )
    except TimeoutPolicyError:
        logger.warning("[DASHBOARD TIMEOUT] bundle degraded | user_id=%s", current_user.id)
        degraded = {
            "status": "degraded",
            "error": "dashboard_timeout",
            "message": "Dashboard snapshot timed out. Cached or partial data may still be available.",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        return _normalize_dashboard_payload(degraded, channel="dashboard.bundle")


async def build_realtime_payload(db: Session, current_user: User) -> dict[str, Any]:
    async def _build() -> dict[str, Any]:
        user_id = str(current_user.id)
        heart_rate, steps, health_score, forecast, preventive, recommended_tests, google_fit_status = await asyncio.gather(
            _run_user_slice(user_id, lambda session, user: _serialize_vitals_slice(session, user, "heart_rate", "24h")),
            _run_user_slice(user_id, lambda session, user: _serialize_vitals_slice(session, user, "steps", "24h")),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_health_score(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_health_forecast(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_preventive_intelligence(user, session)),
            _run_user_slice(user_id, lambda session, user: dashboard_svc.get_recommended_tests(user, session), fallback_data=[]),
            _run_user_slice(user_id, lambda session, user: GoogleFitService.get_status(session, user)),
        )
        google_fit = {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": google_fit_status if isinstance(google_fit_status, dict) else {},
            "last_updated": google_fit_status.get("last_synced_at") if isinstance(google_fit_status, dict) else None,
        }
        payload = {
            "healthScore": health_score,
            "forecast": forecast,
            "preventive": preventive,
            "steps": steps,
            "heart_rate": heart_rate,
            "googleFit": google_fit,
            "recommendedTests": recommended_tests,
        }
        payload["last_updated"] = _dashboard_last_updated(payload)
        return _normalize_dashboard_payload(payload, channel="dashboard.realtime")

    try:
        return await run_with_timeout(
            _build(),
            timeout_seconds=DASHBOARD_AGGREGATION_TIMEOUT_SECONDS,
            operation="dashboard_realtime_payload",
        )
    except TimeoutPolicyError:
        logger.warning("[DASHBOARD TIMEOUT] realtime degraded | user_id=%s", current_user.id)
        degraded = {
            "status": "degraded",
            "error": "dashboard_timeout",
            "message": "Realtime payload timed out. Retaining last known dashboard state.",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        return _normalize_dashboard_payload(degraded, channel="dashboard.realtime")


def _build_psycopg2_kwargs(source_engine) -> dict[str, Any]:
    url = source_engine.url
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
    for key in ("sslmode", "channel_binding", "application_name", "options"):
        if url.query.get(key):
            kwargs[key] = url.query[key]
    return kwargs

_listener_threads: list[threading.Thread] = []
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

        try:
            payload = await build_realtime_payload(db, user)
        except Exception:
            logger.exception("[Dashboard WS] snapshot build failed | user_id=%s", user_id)
            await dashboard_connection_manager.broadcast(
                str(user.id),
                _degraded_dashboard_message(str(user.id), reason="snapshot_build_failed"),
            )
            return
        await dashboard_connection_manager.broadcast_snapshot(str(user.id), payload)
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


def _listen_for_dashboard_updates(source_engine) -> None:
    kwargs = _build_psycopg2_kwargs(source_engine)
    listener_name = f"{source_engine.url.host or 'db'}:{source_engine.url.database or 'database'}"
    while not _listener_stop.is_set():
        conn = None
        try:
            conn = psycopg2.connect(**kwargs)
            conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute("LISTEN dashboard_updates;")
            logger.info("[Dashboard WS] LISTEN dashboard_updates active | target=%s", listener_name)

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
                logger.warning("[Dashboard WS] Listener error | target=%s error=%s", listener_name, exc)
                time.sleep(2)
        finally:
            if conn is not None:
                with suppress(Exception):
                    conn.close()


def start_dashboard_realtime_listener(loop: asyncio.AbstractEventLoop) -> None:
    global _listener_threads, _listener_loop
    if any(thread.is_alive() for thread in _listener_threads):
        _listener_loop = loop
        return

    _listener_stop.clear()
    _listener_loop = loop
    _listener_threads = []
    for index, listener_engine in enumerate(get_listener_engines(), start=1):
        thread = threading.Thread(
            target=_listen_for_dashboard_updates,
            args=(listener_engine,),
            name=f"dashboard-realtime-listener-{index}",
            daemon=True,
        )
        thread.start()
        _listener_threads.append(thread)
    logger.info("[Dashboard WS] Realtime listener started | listeners=%s", len(_listener_threads))


def stop_dashboard_realtime_listener() -> None:
    global _listener_threads, _listener_loop
    _listener_stop.set()
    for thread in _listener_threads:
        if thread.is_alive():
            thread.join(timeout=3)
    _listener_threads = []
    _listener_loop = None
