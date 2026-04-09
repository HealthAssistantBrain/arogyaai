import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import modular routers
from routes import auth, intelligence, users, prediction, dashboard, google_fit, vitals, notifications, user_data, reports

from database.session import engine
from core.config import settings
from services.auto_fetch_scheduler import start_auto_fetch_scheduler, stop_auto_fetch_scheduler

# Critical: import all models so they register on Base.metadata
import models  # noqa: F401

logger = logging.getLogger("backend_main")

app = FastAPI(
    title="ArogyaAI Main Backend",
    description="Orchestrator API routing to specialized Microservices.",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_APP_URL, "http://localhost:5173"],
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


@app.get("/health", tags=["System"])
def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})


# Mount modular routers (prefixes now managed in routers)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(intelligence.router)
app.include_router(prediction.router)
app.include_router(dashboard.router)
app.include_router(google_fit.router)
app.include_router(reports.router)
app.include_router(vitals.router)
app.include_router(notifications.router)
app.include_router(user_data.router)


@app.on_event("startup")
async def _startup_scheduler():
    async def _start_background_services():
        from sqlalchemy import text

        def _check_db_connection():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        try:
            await asyncio.to_thread(_check_db_connection)
            logger.info("DB Connected")
        except Exception as exc:
            logger.warning("DB Connected check failed during startup: %s", exc)
        start_auto_fetch_scheduler()
        logger.info("Scheduler Started")

    logger.info("App Ready")
    asyncio.create_task(_start_background_services())


@app.on_event("shutdown")
def _shutdown_scheduler():
    stop_auto_fetch_scheduler()
