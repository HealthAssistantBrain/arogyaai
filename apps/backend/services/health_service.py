from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Engine

from core.redis_resilience import get_resilient_redis_pool
from database.session import (
    ANALYTICS_DB_MODE,
    analytics_reads_from_primary,
    analytics_runtime_enabled,
    analytics_engine,
    analytics_direct_engine,
    engine as primary_engine,
)
from services.ollama_client import probe_ollama_health
from services.startup_lifecycle import startup_lifecycle
from services.supabase_sdk_validation import get_supabase_sdk_validation_snapshot
from services.supabase_jwt_verifier import get_supabase_auth_snapshot
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.qdrant import probe_qdrant_health

logger = logging.getLogger("health_service")

DB_PROBE_SQL = "SELECT 1"
HTTP_TIMEOUT = httpx.Timeout(2.0, connect=1.0)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
PRIMARY_DB_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_PRIMARY_DB_TIMEOUT_SECONDS", "4.0"))
ANALYTICS_DB_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_ANALYTICS_DB_TIMEOUT_SECONDS", "12.0"))
TIMESCALE_PROBE_TIMEOUT_SECONDS = float(os.getenv("HEALTH_TIMESCALE_TIMEOUT_SECONDS", "12.0"))
OPTIONAL_PROBE_BUDGET_SECONDS = float(os.getenv("HEALTH_OPTIONAL_PROBE_BUDGET_SECONDS", "2.5"))
READINESS_CACHE_TTL_SECONDS = max(1.0, float(os.getenv("HEALTH_READINESS_CACHE_TTL_SECONDS", "5.0")))
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

AUTH_HEALTHY_STATUSES = {"healthy", "warming"}
LIFECYCLE_HEALTHY_STATUSES = {"ready", "warming", "skipped"}
_READINESS_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_probe_timeout_result(key: str) -> dict[str, Any]:
    logger.warning("[Health] Optional %s probe exceeded readiness budget", key)
    return {
        "status": "degraded",
        "error": "probe_budget_exceeded",
        "timeout_budget_seconds": OPTIONAL_PROBE_BUDGET_SECONDS,
    }


def _cache_readiness_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _READINESS_CACHE["payload"] = payload
    _READINESS_CACHE["expires_at"] = time.monotonic() + READINESS_CACHE_TTL_SECONDS
    return payload


def _get_cached_readiness_payload() -> dict[str, Any] | None:
    cached = _READINESS_CACHE.get("payload")
    expires_at = float(_READINESS_CACHE.get("expires_at") or 0.0)
    if cached and time.monotonic() < expires_at:
        return cached
    return None


def _normalize_lifecycle_status(status: str | None) -> str:
    normalized = str(status or "warming").lower()
    if normalized == "ready":
        return "ok"
    if normalized == "deferred":
        return "warming"
    if normalized == "failed":
        return "degraded"
    return normalized


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

    started_at = datetime.now(timezone.utc)
    try:
        pool = await get_resilient_redis_pool("health-probe", url=REDIS_URL)
        await asyncio.wait_for(pool.ping(), timeout=1.5)
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
    cached_payload = _get_cached_readiness_payload()
    if cached_payload is not None:
        return cached_payload

    tasks: dict[str, asyncio.Task[Any]] = {
        "db": asyncio.create_task(
            _check_database(
                primary_engine,
                label="primary_db",
                timeout_seconds=PRIMARY_DB_PROBE_TIMEOUT_SECONDS,
            )
        ),
        "redis": asyncio.create_task(_check_redis()),
    }
    order = [
        "db",
        "redis",
        "package_compatibility",
        "supabase_auth",
        "prediction_service",
        "rag_service",
        "analytics_db",
        "timescale",
        "qdrant",
        "ollama",
        "nvidia_provider",
        "memory",
        "google_fit_worker",
        "dashboard_listener",
        "emergency_worker",
    ]

    results: dict[str, Any] = {}
    try:
        results["db"] = await tasks["db"]
    except Exception as exc:
        results["db"] = exc
    try:
        results["redis"] = await tasks["redis"]
    except Exception as exc:
        results["redis"] = exc

    lifecycle_snapshot = startup_lifecycle.snapshot()
    lifecycle_services = lifecycle_snapshot.get("services", {}) if isinstance(lifecycle_snapshot, dict) else {}

    services: dict[str, str] = {}
    checks: dict[str, dict[str, Any]] = {}

    for key in order:
        if key == "package_compatibility":
            snapshot = get_supabase_sdk_validation_snapshot()
            status = "ok" if snapshot.get("status") == "healthy" else "degraded"
            services[key] = status
            checks[key] = snapshot
            continue

        if key == "supabase_auth":
            snapshot = get_supabase_auth_snapshot()
            auth_status = str(snapshot.get("status") or "warming").lower()
            services[key] = auth_status
            checks[key] = snapshot
            continue

        if key in {"prediction_service", "rag_service", "analytics_db", "timescale", "qdrant", "ollama", "nvidia_provider", "memory", "google_fit_worker", "dashboard_listener", "emergency_worker"}:
            service_snapshot = lifecycle_services.get(key, {})
            normalized_status = _normalize_lifecycle_status(service_snapshot.get("status"))
            services[key] = normalized_status
            checks[key] = {
                "status": normalized_status,
                **service_snapshot,
            }
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

    core_status = (
        "healthy"
        if services.get("db") in {"ok", "skipped"}
        and services.get("package_compatibility") in {"ok", "skipped"}
        else "down"
    )
    overall_status = "ok" if core_status == "healthy" else "down"

    if services.get("supabase_auth") not in AUTH_HEALTHY_STATUSES:
        logger.warning(
            "[Health] Supabase auth dependency is not ready | status=%s cache_state=%s error=%s",
            services.get("supabase_auth"),
            checks.get("supabase_auth", {}).get("cache_state"),
            checks.get("supabase_auth", {}).get("last_fetch_error"),
        )

    payload = _cache_readiness_payload({
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
    })
    return payload
