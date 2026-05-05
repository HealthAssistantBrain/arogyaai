from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from database.session import engine

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("health_service")

DB_PROBE_SQL = "SELECT 1"
HTTP_TIMEOUT = httpx.Timeout(2.0, connect=1.0)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
SERVICE_URLS = {
    "prediction_service": os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8000").strip(),
    "rag_service": os.getenv("RAG_SERVICE_URL", "http://rag-service:8000").strip(),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _check_database() -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)

    def _probe() -> None:
        with engine.connect() as conn:
            conn.exec_driver_sql(DB_PROBE_SQL)

    try:
        await asyncio.wait_for(asyncio.to_thread(_probe), timeout=4.0)
        return {
            "status": "ok",
            "latency_ms": round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000, 2),
        }
    except asyncio.TimeoutError:
        logger.warning("[Health] Database probe timed out")
        return {
            "status": "degraded",
            "error": "database_timeout",
        }
    except Exception as exc:
        logger.warning("[Health] Database probe failed: %s", exc)
        return {
            "status": "degraded",
            "error": "database_unavailable",
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


async def get_system_readiness() -> dict[str, Any]:
    """
    Lightweight readiness probe for the backend.

    The function never raises, never performs heavy work, and returns a
    structured snapshot of the dependency state.
    """
    db_task = _check_database()
    redis_task = _check_redis()
    external_tasks = [
        _check_http_service(service_name, base_url)
        for service_name, base_url in SERVICE_URLS.items()
    ]

    results = await asyncio.gather(db_task, redis_task, *external_tasks, return_exceptions=True)

    services: dict[str, str] = {}
    checks: dict[str, dict[str, Any]] = {}
    order = ["db", "redis", *SERVICE_URLS.keys()]

    for key, result in zip(order, results, strict=False):
        if isinstance(result, Exception):
            logger.error("[Health] Unhandled health probe failure for %s: %s", key, result)
            services[key] = "degraded"
            checks[key] = {
                "status": "degraded",
                "error": "probe_failed",
            }
            continue

        status = str(result.get("status", "degraded"))
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
            if key != "db"
        },
        "checked_at": _utc_now(),
    }
