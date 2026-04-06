from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import modular routers
from routes import auth, intelligence, users, prediction, dashboard, google_fit, vitals

from database.session import engine
from core.config import settings

# Critical: import all models so they register on Base.metadata
import models  # noqa: F401

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
    """
    Deep health check: verifies connectivity to Postgres and Redis.
    Returns 200 if all services are healthy, 503 if any dependency is down.
    Used by docker healthchecks and the frontend maintenance-mode logic.
    """
    from sqlalchemy import text
    import os

    db_status = "error"
    redis_status = "error"
    errors = []

    # Postgres check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        errors.append(f"postgres: {str(e)[:80]}")

    # Redis check
    try:
        import redis as redis_lib
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis_lib.from_url(redis_url, socket_timeout=2)
        r.ping()
        redis_status = "ok"
    except Exception as e:
        errors.append(f"redis: {str(e)[:80]}")

    all_healthy = (db_status == "connected" and redis_status == "ok")
    http_status = 200 if all_healthy else 503

    body = {
        "success": all_healthy,
        "status": "ready" if all_healthy else "fallback",
        "data": {
            "postgres": db_status,
            "redis": redis_status
        },
        "error": ", ".join(errors) if errors else None
    }

    return JSONResponse(status_code=http_status, content=body)


# Mount modular routers (prefixes now managed in routers)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(intelligence.router)
app.include_router(prediction.router)
app.include_router(dashboard.router)
app.include_router(google_fit.router)
app.include_router(vitals.router)
