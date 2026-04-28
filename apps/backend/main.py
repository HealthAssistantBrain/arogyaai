import asyncio
import logging
import sys
import secrets
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

# Import modular routers
from routes import aqi, auth, intelligence, users, prediction, dashboard, google_fit, vitals, notifications, user_data, reports, sleep, insights, lab_results, timeline, dashboard_ws

from database.session import engine
from core.config import settings
from core.pipeline_logger import log_pipeline, log_pipeline_section
from services.dashboard_realtime import start_dashboard_realtime_listener, stop_dashboard_realtime_listener
from services.health_service import get_system_readiness
from workers.google_fit_worker import start_google_fit_worker, stop_google_fit_worker

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


def _health_logic():
    return {"status": "ok"}

@app.get("/health", tags=["System"])
async def health_root():
    return JSONResponse(status_code=200, content=_health_logic())

@app.get("/api/v1/health", tags=["System"])
async def health_api():
    try:
        return JSONResponse(status_code=200, content=await get_system_readiness())
    except Exception as exc:
        logger.exception("Health readiness probe failed: %s", exc)
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
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
app.include_router(user_data.router)
app.include_router(sleep.router)
app.include_router(insights.router)
app.include_router(timeline.router)


@app.on_event("startup")
async def _startup_scheduler():
    from sqlalchemy import text

    def _check_db_connection():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    log_pipeline_section("PIPELINE STARTUP")
    log_pipeline("system", step="initializing", status="running", data="pending")

    try:
        await asyncio.to_thread(_check_db_connection)
        logger.info("DB Connected")
        log_pipeline("database", step="connection_check", status="healthy", data="ok")
    except Exception as exc:
        logger.warning("DB Connected check failed during startup: %s", exc)
        log_pipeline("database", step="connection_check", status="unhealthy", data="failed")

    try:
        start_google_fit_worker()
        logger.info("Google Fit background worker started")
        log_pipeline("ingestion", step="google_fit_worker", status="healthy", data="started")
    except Exception as exc:
        logger.exception("Google Fit worker failed to start: %s", exc)
        log_pipeline("ingestion", step="google_fit_worker", status="unhealthy", data="failed")

    try:
        start_dashboard_realtime_listener(asyncio.get_running_loop())
        logger.info("Dashboard realtime listener started")
        log_pipeline("realtime", step="dashboard_listener", status="healthy", data="started")
    except Exception as exc:
        logger.exception("Dashboard realtime listener failed to start: %s", exc)
        log_pipeline("realtime", step="dashboard_listener", status="unhealthy", data="failed")

    log_pipeline("system", step="all_pipelines_initialized", status="healthy", data="ready")
    logger.info("App Ready")


@app.on_event("shutdown")
def _shutdown_scheduler():
    stop_google_fit_worker()
    stop_dashboard_realtime_listener()
