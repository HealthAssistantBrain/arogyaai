from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Engine

from database.session import (
    ANALYTICS_DB_MODE,
    analytics_reads_from_primary,
    analytics_runtime_enabled,
    analytics_engine,
    analytics_direct_engine,
    engine as primary_engine,
)
from services.ollama_client import probe_ollama_health
from services.supabase_jwt_verifier import get_supabase_auth_snapshot
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.qdrant import probe_qdrant_health

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("health_service")

DB_PROBE_SQL = "SELECT 1"
HTTP_TIMEOUT = httpx.Timeout(2.0, connect=1.0)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
PRIMARY_DB_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_PRIMARY_DB_TIMEOUT_SECONDS", "4.0"))
ANALYTICS_DB_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_ANALYTICS_DB_TIMEOUT_SECONDS", "12.0"))
TIMESCALE_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_TIMESCALE_TIMEOUT_SECONDS", "12.0"))
OPTIONAL_PROBE_BUDGET_SECONDS = float(os.getenv("HEALTH_OPTIONAL_PROBE_BUDGET_SECONDS", "2.5"))
SERVICE_URLS = {
    "prediction_service": os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8000").strip(),
    "rag_service": os.getenv("RAG_SERVICE_URL", "http://rag-service:8000").strip(),
}
ANALYTICS_HYPERTABLES = (
    "wearable_metrics",
    "user_vitals",
    "risk_scores",
    "health_scores",
    "feature_snapshots",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_probe_timeout_result(key: str) -> dict[str, Any]:
    logger.warning("[Health] Optional %s probe exceeded readiness budget", key)
    return {
        "status": "degraded",
        "error": "probe_budget_exceeded",
        "timeout_budget_seconds": OPTIONAL_PROBE_BUDGET_SECONDS,
    }


async def _check_database(
    engine: Engine,
    *,
    label: str,
    timeout_seconds: float = PRIMARY_DB_PROBE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)

    def _probe() -> None:
        with engine.connect() as conn:
            conn.exec_driver_sql(DB_PROBE_SQL)

    try:
        await asyncio.wait_for(asyncio.to_thread(_probe), timeout=timeout_seconds)
        return {
            "status": "ok",
            "target": label,
            "latency_ms": round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 2),
        }
    except asyncio.TimeoutError:
        logger.warning("[Health] %s probe timed out", label)
        return {
            "status": "degraded",
            "target": label,
            "error": f"{label}_timeout",
        }
    except Exception as exc:
        logger.warning("[Health] %s probe failed: %s", label, exc)
        return {
            "status": "degraded",
            "target": label,
            "error": f"{label}_unavailable",
        }


async def _check_redis() -> dict[str, Any]:
    if not REDIS_URL:
        return {
            "status": "skipped",
            "error": None,
        }

    if Redis is None:
        return {
            "status": "degraded",
            "error": "redis_client_unavailable",
        }

    started_at = datetime.now(timezone.utc)
    client = Redis.from_url(REDIS_URL, socket_connect_timeout=1.0, socket_timeout=1.0, decode_responses=True)
    try:
        await client.ping()
        return {
            "status": "ok",
            "latency_ms": round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 2),
        }
    except Exception as exc:
        logger.warning("[Health] Redis probe failed: %s", exc)
        return {
            "status": "degraded",
            "error": "redis_unavailable",
        }
    finally:
        try:
            await client.aclose()
        except Exception:
            logger.debug("[Health] Redis client close failed", exc_info=True)


async def _check_http_service(service_name: str, base_url: str) -> dict[str, Any]:
    if not base_url:
        return {
            "status": "skipped",
            "error": None,
        }

    started_at = datetime.now(timezone.utc)
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(health_url)

        payload: dict[str, Any] = {}
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                body = response.json()
                if isinstance(body, dict):
                    payload = body
        except Exception:
            payload = {}

        service_status = str(payload.get("status", "")).lower()
        if response.is_success and service_status in {"ok", "ready"}:
            return {
                "status": "ok",
                "http_status": response.status_code,
                "latency_ms": round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 2),
            }

        return {
            "status": "degraded",
            "http_status": response.status_code,
            "error": f"{service_name}_unhealthy",
        }
    except Exception as exc:
        logger.warning("[Health] %s probe failed: %s", service_name, exc)
        return {
            "status": "degraded",
            "error": f"{service_name}_unreachable",
        }


async def _fetch_timescale_status(timeout_seconds: float = TIMESCALE_PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    probe_engine = analytics_direct_engine if analytics_runtime_enabled() else primary_engine
    provider = "neon" if analytics_runtime_enabled() else "local_timescale_fallback"

    def _probe() -> dict[str, Any]:
        with probe_engine.connect() as conn:
            extension_version = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            ).scalar()
            if not extension_version:
                return {
                    "status": "degraded",
                    "provider": provider,
                    "extension_version": None,
                    "hypertables": [],
                    "continuous_aggregates": [],
                }
            hypertables = conn.execute(
                text(
                    """
                    SELECT hypertable_name
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = ANY(:names)
                    ORDER BY hypertable_name
                    """
                ),
                {"names": list(ANALYTICS_HYPERTABLES)},
            ).scalars().all()
            continuous_aggregates = conn.execute(
                text(
                    """
                    SELECT view_name
                    FROM timescaledb_information.continuous_aggregates
                    ORDER BY view_name
                    """
                )
            ).scalars().all()
        return {
            "status": "ok" if extension_version else "degraded",
            "provider": provider,
            "extension_version": extension_version,
            "hypertables": hypertables,
            "continuous_aggregates": continuous_aggregates,
        }

    try:
        return await asyncio.wait_for(asyncio.to_thread(_probe), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return {
            "status": "degraded",
            "provider": provider,
            "error": "timescale_probe_timeout",
        }
    except Exception as exc:
        logger.warning("[Health] Timescale probe failed: %s", exc)
        return {
            "status": "degraded",
            "provider": provider,
            "error": "timescale_probe_failed",
        }


async def get_neon_health() -> dict[str, Any]:
    if not analytics_runtime_enabled():
        return {
            "status": "skipped",
            "provider": "local_timescale_fallback",
            "mode": "primary",
            "read_strategy": "primary",
            "checked_at": _utc_now(),
        }

    result = await _check_database(
        analytics_engine,
        label="analytics_db",
        timeout_seconds=ANALYTICS_DB_PROBE_TIMEOUT_SECONDS,
    )
    result["provider"] = "neon"
    result["mode"] = ANALYTICS_DB_MODE
    result["read_strategy"] = "primary" if analytics_reads_from_primary() else "neon"
    result["checked_at"] = _utc_now()
    return result


async def get_timescale_health() -> dict[str, Any]:
    payload = await _fetch_timescale_status(timeout_seconds=TIMESCALE_PROBE_TIMEOUT_SECONDS)
    payload["checked_at"] = _utc_now()
    return payload


async def get_qdrant_health() -> dict[str, Any]:
    payload = await asyncio.to_thread(probe_qdrant_health, RagSettings())
    payload["checked_at"] = _utc_now()
    return payload


async def get_ollama_health() -> dict[str, Any]:
    payload = await probe_ollama_health(
        RagSettings(),
        warmup=os.getenv("OLLAMA_HEALTH_WARMUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
    )
    payload["checked_at"] = _utc_now()
    return payload


async def get_system_readiness() -> dict[str, Any]:
    """
    Lightweight readiness probe for the backend.

    The function never raises, never performs heavy work, and returns a
    structured snapshot of the dependency state.
    """
    started_at = datetime.now(timezone.utc)
    tasks: dict[str, asyncio.Task[Any]] = {
        "db": asyncio.create_task(
            _check_database(
                primary_engine,
                label="primary_db",
                timeout_seconds=PRIMARY_DB_PROBE_TIMEOUT_SECONDS,
            )
        ),
        "redis": asyncio.create_task(_check_redis()),
        "qdrant": asyncio.create_task(get_qdrant_health()),
        "ollama": asyncio.create_task(get_ollama_health()),
    }
    for service_name, base_url in SERVICE_URLS.items():
        tasks[service_name] = asyncio.create_task(_check_http_service(service_name, base_url))

    if analytics_runtime_enabled():
        tasks["analytics_db"] = asyncio.create_task(
            _check_database(
                analytics_engine,
                label="analytics_db",
                timeout_seconds=ANALYTICS_DB_PROBE_TIMEOUT_SECONDS,
            )
        )
        tasks["timescale"] = asyncio.create_task(
            _fetch_timescale_status(timeout_seconds=TIMESCALE_PROBE_TIMEOUT_SECONDS)
        )

    order = ["db", "redis", "qdrant", "ollama", *SERVICE_URLS.keys()]
    if analytics_runtime_enabled():
        order.extend(["analytics_db", "timescale"])
    order.append("supabase_auth")

    results: dict[str, Any] = {}
    try:
        results["db"] = await tasks["db"]
    except Exception as exc:
        results["db"] = exc

    optional_keys = [key for key in order if key != "db" and key in tasks]
    remaining_budget = max(
        0.0,
        OPTIONAL_PROBE_BUDGET_SECONDS - (datetime.now(timezone.utc) - started_at).total_seconds(),
    )

    task_to_key = {tasks[key]: key for key in optional_keys}
    if task_to_key:
        done, pending = await asyncio.wait(task_to_key.keys(), timeout=remaining_budget)

        for task in done:
            if task.cancelled():
                results[task_to_key[task]] = _optional_probe_timeout_result(task_to_key[task])
                continue
            exception = task.exception()
            results[task_to_key[task]] = task.result() if exception is None else exception

        for task in pending:
            key = task_to_key[task]
            task.cancel()
            results[key] = _optional_probe_timeout_result(key)

        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    services: dict[str, str] = {}
    checks: dict[str, dict[str, Any]] = {}

    for key in order:
        if key == "supabase_auth":
            snapshot = get_supabase_auth_snapshot()
            services[key] = "ok" if snapshot.get("status") == "ok" else "degraded"
            checks[key] = snapshot
            continue

        result = results.get(key)
        if isinstance(result, Exception):
            logger.error("[Health] Unhandled health probe failure for %s: %s", key, result)
            services[key] = "degraded"
            checks[key] = {
                "status": "degraded",
                "error": "probe_failed",
            }
            continue

        status = str(result.get("status", "degraded"))
        if key == "qdrant":
            services[key] = "ok" if status == "healthy" else status
            checks[key] = result
            continue
        services[key] = status
        checks[key] = result

    core_status = "healthy" if services.get("db") in {"ok", "skipped"} else "down"
    overall_status = "ok" if core_status == "healthy" else "down"

    return {
        "status": overall_status,
        "core_system": core_status,
        "maintenance_eligible": core_status == "down",
        "services": services,
        "checks": checks,
        "external_services": {
            key: value
            for key, value in services.items()
            if key not in {"db", "analytics_db", "timescale"}
        },
        "checked_at": _utc_now(),
    }
