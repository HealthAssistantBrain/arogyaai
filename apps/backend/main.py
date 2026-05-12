import asyncio
import logging
import os
import sys
import secrets
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

# Import modular routers
from routes import aqi, auth, intelligence, users, prediction, dashboard, google_fit, vitals, notifications, user_data, reports, sleep, insights, lab_results, timeline, dashboard_ws, clinical_history, settings as settings_routes, devices as devices_routes, chat, rag, feedback, profile, symptoms, report_generation, orchestrator as orchestrator_routes, memory_api
from api.v1 import doctor as doctor_routes
from api.v1 import emergency as emergency_routes

from database.session import analytics_runtime_enabled, dispose_engines, engine, log_pool_snapshot
from core.config import settings
from core.pipeline_logger import log_pipeline, log_pipeline_section
from core.serialization.safe_response import SafeJSONResponse as JSONResponse
from pipelines.rag_pipeline.config import RagSettings
from services.dashboard_realtime import start_dashboard_realtime_listener, stop_dashboard_realtime_listener
from services.health_service import (
    _check_http_service,
    _check_redis,
    get_neon_health,
    get_ollama_health,
    get_qdrant_health,
    get_system_readiness,
    get_timescale_health,
)
from services.ollama_client import probe_ollama_health
from services.startup_lifecycle import startup_lifecycle
from services.supabase_sdk_validation import (
    SupabaseSDKCompatibilityError,
    ensure_supabase_sdk_compatibility,
)
from services.supabase_jwt_verifier import supabase_jwt_verifier
from workers.emergency_worker import start_emergency_worker, stop_emergency_worker
from workers.google_fit_worker import start_google_fit_worker, stop_google_fit_worker
from workers.preventive_worker import start_preventive_worker, stop_preventive_worker

# Critical: import all models so they register on Base.metadata
import models  # noqa: F401

logger = logging.getLogger("backend_main")

app = FastAPI(
    title="ArogyaAI Main Backend",
    description="Orchestrator API routing to specialized Microservices.",
    version="1.0.0"
)


# ── Anti-local-storage guard ──────────────────────────────────────────────────
# Raise at startup if the Supabase storage key is not set.
# Local file storage has been removed — this prevents silent upload failures.
if not settings.SUPABASE_SERVICE_ROLE_KEY:
    import warnings
    warnings.warn(
        "SUPABASE_SERVICE_ROLE_KEY is not set. "
        "Report uploads will fail until this key is configured. "
        "Set SUPABASE_SERVICE_ROLE_KEY in your .env file.",
        RuntimeWarning,
        stacklevel=2,
    )
# ─────────────────────────────────────────────────────────────────────────────


frontend_origins = list(
    dict.fromkeys(
        [
            settings.FRONTEND_APP_URL.rstrip("/"),
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status": "fallback" if exc.status_code >= 500 else "ready",
            "data": None,
            "error": str(exc.detail)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "status": "ready",
            "data": None,
            "error": "Validation error: " + str(exc.errors())
        }
    )


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}
    exempt_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/oauth",
        "/api/v1/auth/social-login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/refresh-token",
        "/api/v1/health",
        "/health",
    }

    if request.method in unsafe_methods:
        path = request.url.path
        has_cookie_session = bool(request.cookies.get("access_token") or request.cookies.get("refresh_token"))
        is_exempt = path in exempt_paths or any(path.startswith(prefix) for prefix in ("/docs", "/openapi.json", "/redoc"))

        if has_cookie_session and not is_exempt:
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("x-csrf-token")

            if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "status": "ready",
                        "data": None,
                        "error": "CSRF validation failed",
                    },
                )

    response = await call_next(request)
    return response


@app.middleware("http")
async def route_audit_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path

    if response.status_code == 404:
        logger.warning("404 route not found | method=%s path=%s", request.method, path)
    elif path.startswith("/api/") and not path.startswith("/api/v1"):
        logger.warning(
            "Misrouted API request | method=%s path=%s status=%s expected_prefix=/api/v1",
            request.method,
            path,
            response.status_code,
        )

    return response


@app.get("/health", tags=["System"])
async def health_root():
    try:
        return JSONResponse(status_code=200, content=await get_system_readiness())
    except Exception as exc:
        logger.exception("Health probe failed: %s", exc)
        return JSONResponse(
            status_code=200,
            content={
                "status": "down",
                "core_system": "down",
                "maintenance_eligible": True,
                "services": {"db": "degraded"},
                "checks": {"db": {"status": "degraded", "error": "probe_failed"}},
            },
        )

@app.get("/api/v1/health", tags=["System"])
async def health_api():
    try:
        return JSONResponse(status_code=200, content=await get_system_readiness())
    except Exception as exc:
        logger.exception("Health readiness probe failed: %s", exc)
        return JSONResponse(
            status_code=200,
            content={
                "status": "down",
                "core_system": "down",
                "maintenance_eligible": True,
                "services": {
                    "db": "degraded",
                },
                "checks": {
                    "db": {
                        "status": "degraded",
                        "error": "probe_failed",
                    }
                },
            },
        )


@app.get("/health/neon", tags=["System"])
async def health_neon_root():
    return JSONResponse(status_code=200, content=await get_neon_health())


@app.get("/api/v1/health/neon", tags=["System"])
async def health_neon_api():
    return JSONResponse(status_code=200, content=await get_neon_health())


@app.get("/health/timescale", tags=["System"])
async def health_timescale_root():
    return JSONResponse(status_code=200, content=await get_timescale_health())


@app.get("/api/v1/health/timescale", tags=["System"])
async def health_timescale_api():
    return JSONResponse(status_code=200, content=await get_timescale_health())


@app.get("/health/qdrant", tags=["System"])
async def health_qdrant_root():
    return JSONResponse(status_code=200, content=await get_qdrant_health())


@app.get("/api/v1/health/qdrant", tags=["System"])
async def health_qdrant_api():
    return JSONResponse(status_code=200, content=await get_qdrant_health())


@app.get("/health/ollama", tags=["System"])
async def health_ollama_root():
    return JSONResponse(status_code=200, content=await get_ollama_health())


@app.get("/api/v1/health/ollama", tags=["System"])
async def health_ollama_api():
    return JSONResponse(status_code=200, content=await get_ollama_health())


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


OPTIONAL_STARTUP_TIMEOUT_SECONDS = max(5.0, _env_float("OPTIONAL_STARTUP_TIMEOUT_SECONDS", 45.0))
TIER2_INITIAL_DELAY_SECONDS = max(0.25, _env_float("STARTUP_TIER2_INITIAL_DELAY_SECONDS", 1.0))
TIER3_INITIAL_DELAY_SECONDS = max(2.0, _env_float("STARTUP_TIER3_INITIAL_DELAY_SECONDS", 12.0))
TIER3_STEP_DELAY_SECONDS = max(1.0, _env_float("STARTUP_TIER3_STEP_DELAY_SECONDS", 4.0))


async def safe_init_rag():
    from pipelines.rag_pipeline.config import RagSettings
    from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever

    retries = max(1, _env_int("RAG_STARTUP_RETRIES", 5))
    delay_seconds = max(0.0, _env_float("RAG_STARTUP_RETRY_DELAY_SECONDS", 2.0))

    for attempt in range(1, retries + 1):
        try:
            rag_state = await asyncio.to_thread(
                MedicalKnowledgeRetriever(RagSettings()).assert_index_ready
            )
            print(f"[RAG INIT] ready: {rag_state}")
            return rag_state
        except Exception as exc:
            print(f"[RAG INIT] attempt {attempt} failed: {exc}")
            logger.warning(
                "RAG Qdrant index check attempt failed | attempt=%s/%s error=%s",
                attempt,
                retries,
                exc,
            )
            if attempt < retries and delay_seconds:
                await asyncio.sleep(delay_seconds)

    print("[RAG INIT] FAILED - continuing without RAG")
    return None


async def _run_optional_startup_task(task_name: str, task_coro, *, timeout_seconds: float) -> None:
    started_at = time.perf_counter()
    logger.info("[Startup] Optional task started | task=%s timeout=%ss", task_name, timeout_seconds)
    try:
        await asyncio.wait_for(task_coro, timeout=timeout_seconds)
        logger.info(
            "[Startup] Optional task completed | task=%s duration_ms=%s",
            task_name,
            round((time.perf_counter() - started_at) * 1000, 2),
        )
    except asyncio.TimeoutError:
        logger.warning(
            "[Startup] Optional task timed out | task=%s timeout=%ss",
            task_name,
            timeout_seconds,
        )
    except Exception as exc:
        logger.exception("[Startup] Optional task failed | task=%s error=%s", task_name, exc)


def _launch_optional_startup_task(app: FastAPI, task_name: str, task_coro, *, timeout_seconds: float) -> None:
    task = asyncio.create_task(
        _run_optional_startup_task(task_name, task_coro, timeout_seconds=timeout_seconds),
        name=f"startup:{task_name}",
    )
    app.state.optional_startup_tasks.add(task)

    def _cleanup(finished_task: asyncio.Task) -> None:
        app.state.optional_startup_tasks.discard(finished_task)

    task.add_done_callback(_cleanup)


# Mount modular routers (prefixes now managed in routers)
app.include_router(auth.router)
app.include_router(aqi.router)
app.include_router(users.router)
app.include_router(intelligence.router)
app.include_router(prediction.router)
app.include_router(dashboard.router)
app.include_router(dashboard_ws.router)
app.include_router(google_fit.router)
app.include_router(google_fit.integration_router)
app.include_router(google_fit.wearable_router)
app.include_router(reports.router)
app.include_router(lab_results.router)
app.include_router(vitals.router)
app.include_router(notifications.router)
app.include_router(settings_routes.router)
app.include_router(devices_routes.router)
app.include_router(user_data.router)
app.include_router(profile.router)
app.include_router(sleep.router)
app.include_router(insights.router)
app.include_router(timeline.router)
app.include_router(clinical_history.router)
app.include_router(symptoms.router)
app.include_router(report_generation.router)
app.include_router(chat.router)
app.include_router(rag.router)
app.include_router(feedback.router)
app.include_router(orchestrator_routes.router)
app.include_router(memory_api.router)
app.include_router(doctor_routes.router)
app.include_router(emergency_routes.router)


@app.on_event("startup")
async def _startup_scheduler():
    from sqlalchemy import text

    def _check_db_connection():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    startup_started_at = time.perf_counter()
    startup_lifecycle.reset()
    startup_lifecycle.set_phase("tier1")
    log_pipeline_section("PIPELINE STARTUP")
    log_pipeline("system", step="initializing", status="running", data="pending")
    startup_lifecycle.mark("core_api", status="running", detail="booting")

    async def _package_compatibility_startup() -> dict[str, str]:
        snapshot = await asyncio.to_thread(ensure_supabase_sdk_compatibility, force=True)
        logger.info(
            "[DEPENDENCY VALIDATION] Locked Supabase SDK ready | packages=%s",
            snapshot.get("packages"),
        )
        log_pipeline(
            "system",
            step="dependency_validation",
            status="healthy",
            data=str(snapshot.get("packages")),
        )
        return {"status": "ready", "detail": snapshot.get("detail", "supabase_sdk_locked")}

    try:
        await startup_lifecycle.run_blocking(
            "package_compatibility",
            _package_compatibility_startup,
            detail="supabase_sdk_validation",
        )
    except SupabaseSDKCompatibilityError as exc:
        logger.critical(
            "[PACKAGE COMPATIBILITY] Backend startup blocked by incompatible Supabase SDK | error=%s",
            exc,
        )
        log_pipeline(
            "system",
            step="dependency_validation",
            status="degraded",
            data=str(exc),
        )
        raise RuntimeError(str(exc)) from exc

    try:
        await startup_lifecycle.run_blocking("db", lambda: asyncio.to_thread(_check_db_connection), detail="connection_check")
        logger.info("DB Connected")
        log_pipeline("database", step="connection_check", status="healthy", data="ok")
    except Exception as exc:
        logger.warning("DB Connected check failed during startup: %s", exc)
        log_pipeline("database", step="connection_check", status="unhealthy", data="failed")

    try:
        redis_status = await startup_lifecycle.run_blocking("redis", _check_redis, detail="ping")
        log_pipeline(
            "redis",
            step="ping",
            status="healthy" if redis_status.get("status") in {"ok", "skipped"} else "degraded",
            data=redis_status.get("error") or "ok",
        )
    except Exception as exc:
        logger.warning("Redis readiness failed during startup: %s", exc)
        log_pipeline("redis", step="ping", status="unhealthy", data="failed")

    startup_lifecycle.mark("auth", status="ready", detail="session_validation_available")
    startup_lifecycle.mark("core_api", status="ready", detail="tier1_ready")
    startup_lifecycle.set_phase("tier2")

    async def _analytics_startup() -> dict[str, str]:
        if not analytics_runtime_enabled():
            startup_lifecycle.mark("analytics_db", status="skipped", detail="analytics_disabled")
            startup_lifecycle.mark("timescale", status="skipped", detail="analytics_disabled")
            return {"status": "skipped"}
        neon_status = await get_neon_health()
        timescale_status = await get_timescale_health()
        startup_lifecycle.mark(
            "analytics_db",
            status="ready" if neon_status.get("status") == "ok" else "degraded",
            detail=neon_status.get("provider", "neon"),
        )
        startup_lifecycle.mark(
            "timescale",
            status="ready" if timescale_status.get("status") == "ok" else "degraded",
            detail=timescale_status.get("provider", "timescale"),
        )
        log_pipeline(
            "analytics_database",
            step="neon_connection_check",
            status="healthy" if neon_status.get("status") == "ok" else "degraded",
            data=neon_status.get("provider", "neon"),
        )
        return {"status": neon_status.get("status", "ok")}

    app.state.rag_state = None
    async def _prediction_service_startup() -> dict:
        status_snapshot = await _check_http_service(
            "prediction_service",
            os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8000").strip(),
        )
        startup_lifecycle.mark(
            "prediction_service",
            status="ready" if status_snapshot.get("status") == "ok" else "degraded",
            detail=status_snapshot.get("error") or "reachable",
        )
        return status_snapshot

    async def _rag_service_startup() -> dict:
        status_snapshot = await _check_http_service(
            "rag_service",
            os.getenv("RAG_SERVICE_URL", "http://rag-service:8000").strip(),
        )
        startup_lifecycle.mark(
            "rag_service",
            status="ready" if status_snapshot.get("status") == "ok" else "degraded",
            detail=status_snapshot.get("error") or "reachable",
        )
        return status_snapshot

    async def _rag_startup() -> dict:
        rag_state = await safe_init_rag()
        app.state.rag_state = rag_state
        if rag_state is None:
            logger.warning("RAG Qdrant index unavailable during startup; continuing in degraded mode")
            log_pipeline("rag", step="qdrant_index_check", status="degraded", data="fallback")
            startup_lifecycle.mark("qdrant", status="degraded", detail="index_unavailable")
            return {"status": "degraded"}

        logger.info("RAG Qdrant index ready | %s", rag_state)
        log_pipeline("rag", step="qdrant_index_check", status="healthy", data=str(rag_state))
        startup_lifecycle.mark("qdrant", status="ready", detail="index_ready")
        return {"status": "ready"}

    async def _ollama_startup() -> dict:
        if not _env_bool("OLLAMA_WARMUP_ON_STARTUP", "false"):
            startup_lifecycle.mark("ollama", status="skipped", detail="warmup_disabled")
            return {"status": "skipped"}
        ollama_state = await probe_ollama_health(RagSettings(), warmup=True)
        logger.info("Ollama warmup status: %s", ollama_state.get("status"))
        log_pipeline(
            "ollama",
            step="warmup",
            status="healthy" if ollama_state.get("status") == "ok" else "degraded",
            data=ollama_state.get("configured_model", "unknown"),
        )
        startup_lifecycle.mark(
            "ollama",
            status="ready" if ollama_state.get("status") == "ok" else "degraded",
            detail=ollama_state.get("configured_model", "unknown"),
        )
        return ollama_state

    async def _supabase_auth_startup() -> dict:
        if not settings.SUPABASE_JWKS_STARTUP_WARMUP:
            startup_lifecycle.mark("supabase_auth", status="skipped", detail="warmup_disabled")
            return {"status": "skipped"}
        snapshot = await supabase_jwt_verifier.warm_cache(reason="startup")
        logger.info(
            "Supabase auth warmup completed | status=%s cache_state=%s keys_cached=%s",
            snapshot.get("status"),
            snapshot.get("cache_state"),
            snapshot.get("keys_cached"),
        )
        log_pipeline(
            "auth",
            step="supabase_jwks_warmup",
            status="healthy" if snapshot.get("status") in {"healthy", "warming"} else "degraded",
            data=snapshot.get("cache_state", "unknown"),
        )
        startup_lifecycle.mark(
            "supabase_auth",
            status="ready" if snapshot.get("status") in {"healthy", "warming"} else "degraded",
            detail=snapshot.get("cache_state", "unknown"),
        )
        return snapshot

    async def _nvidia_startup() -> dict:
        try:
            from services.orchestrator import get_orchestrator

            snapshot = await get_orchestrator().provider_runtime.health_snapshot()
            nvidia_snapshot = (snapshot.get("providers") or {}).get("nvidia", {})
            startup_lifecycle.mark(
                "nvidia_provider",
                status="ready" if str(nvidia_snapshot.get("status") or "").lower() in {"ok", "ready", "healthy"} else "degraded",
                detail=nvidia_snapshot.get("model") or nvidia_snapshot.get("provider") or "nvidia",
            )
            return snapshot
        except Exception as exc:
            startup_lifecycle.mark("nvidia_provider", status="degraded", detail="healthcheck_failed", error=str(exc))
            raise

    async def _memory_startup() -> dict:
        from ai.memory import get_memory_engine

        memory_engine = get_memory_engine()
        print("[MEMORY] verifying storage and warming memory infrastructure")
        logger.info("[MEMORY] verifying storage and warming memory infrastructure")
        verification = await memory_engine.verify_storage()
        print(f"[MEMORY MIGRATION COMPLETE] table=health_memory pk={verification.get('pk_columns')} detail={verification.get('detail')}")
        logger.info(
            "[MEMORY MIGRATION COMPLETE] table=health_memory pk=%s detail=%s",
            verification.get("pk_columns"),
            verification.get("detail"),
        )
        if verification.get("hypertable_ready"):
            print("[MEMORY HYPERTABLE READY] table=health_memory")
            logger.info("[MEMORY HYPERTABLE READY] table=health_memory")
        else:
            print(
                f"[MEMORY] hypertable_ready={verification.get('hypertable_ready')} "
                f"timescale_available={verification.get('timescale_available')}"
            )
            logger.info(
                "[MEMORY] hypertable_ready=%s timescale_available=%s",
                verification.get("hypertable_ready"),
                verification.get("timescale_available"),
            )
        await memory_engine.warmup()
        print("[MEMORY] embeddings collection warmed")
        logger.info("[MEMORY] embeddings collection warmed")
        startup_lifecycle.mark("memory", status=str(verification.get("status") or "ready"), detail=str(verification.get("detail") or "collection_warmed"))
        return verification

    loop = asyncio.get_running_loop()

    async def _start_google_fit_worker_task() -> dict:
        start_google_fit_worker()
        logger.info("Google Fit background worker started")
        log_pipeline("ingestion", step="google_fit_worker", status="healthy", data="started")
        return {"status": "ready"}

    async def _start_dashboard_listener_task() -> dict:
        start_dashboard_realtime_listener(loop)
        logger.info("Dashboard realtime listener started")
        log_pipeline("realtime", step="dashboard_listener", status="healthy", data="started")
        return {"status": "ready"}

    async def _start_emergency_worker_task() -> dict:
        start_emergency_worker()
        logger.info("Emergency detection worker started")
        log_pipeline("realtime", step="emergency_worker", status="healthy", data="started")
        return {"status": "ready"}

    async def _start_preventive_worker_task() -> dict:
        start_preventive_worker()
        logger.info("Preventive intelligence background worker started")
        log_pipeline("realtime", step="preventive_worker", status="healthy", data="started")
        return {"status": "ready"}

    startup_lifecycle.schedule("analytics_db", _analytics_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="analytics_probe")
    startup_lifecycle.schedule("prediction_service", _prediction_service_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="prediction_probe")
    startup_lifecycle.schedule("rag_service", _rag_service_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 1, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="rag_probe")
    if _env_bool("RAG_STARTUP_INDEX_CHECK", "true"):
        startup_lifecycle.schedule("qdrant", _rag_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 2, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="index_check")
    else:
        startup_lifecycle.mark("qdrant", status="skipped", detail="index_check_disabled")
    startup_lifecycle.schedule("ollama", _ollama_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 3, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="warmup")
    startup_lifecycle.schedule("supabase_auth", _supabase_auth_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 4, timeout_seconds=max(1.0, settings.SUPABASE_AUTH_STARTUP_TIMEOUT_SECONDS), detail="jwks_warmup")
    startup_lifecycle.schedule("nvidia_provider", _nvidia_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 5, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="provider_warmup")
    startup_lifecycle.schedule("memory", _memory_startup, delay_seconds=TIER2_INITIAL_DELAY_SECONDS + 6, timeout_seconds=OPTIONAL_STARTUP_TIMEOUT_SECONDS, detail="memory_warmup")

    startup_lifecycle.set_phase("tier3")
    startup_lifecycle.schedule("google_fit_worker", _start_google_fit_worker_task, delay_seconds=TIER3_INITIAL_DELAY_SECONDS, timeout_seconds=15.0, detail="worker_boot")
    startup_lifecycle.schedule("dashboard_listener", _start_dashboard_listener_task, delay_seconds=TIER3_INITIAL_DELAY_SECONDS + TIER3_STEP_DELAY_SECONDS, timeout_seconds=15.0, detail="listener_boot")
    startup_lifecycle.schedule("emergency_worker", _start_emergency_worker_task, delay_seconds=TIER3_INITIAL_DELAY_SECONDS + (TIER3_STEP_DELAY_SECONDS * 2), timeout_seconds=15.0, detail="worker_boot")
    startup_lifecycle.schedule("preventive_worker", _start_preventive_worker_task, delay_seconds=TIER3_INITIAL_DELAY_SECONDS + (TIER3_STEP_DELAY_SECONDS * 3), timeout_seconds=15.0, detail="worker_boot")

    log_pool_snapshot(force=True)
    startup_lifecycle.set_phase("ready")
    log_pipeline("system", step="all_pipelines_initialized", status="healthy", data="ready")
    logger.info(
        "App Ready | startup_duration_ms=%s background_tasks=%s",
        round((time.perf_counter() - startup_started_at) * 1000, 2),
        len(startup_lifecycle.snapshot().get("services", {})),
    )


@app.on_event("shutdown")
async def _shutdown_scheduler():
    await startup_lifecycle.shutdown()
    stop_google_fit_worker()
    stop_dashboard_realtime_listener()
    stop_emergency_worker()
    stop_preventive_worker()
    await supabase_jwt_verifier.aclose()
    log_pool_snapshot(force=True)
    dispose_engines()
