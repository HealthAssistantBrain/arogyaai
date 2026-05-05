import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from database.session import get_db
from routes.users import get_current_user_from_header
from schemas.api_models import GoogleFitConnectRequest, GoogleFitSyncRequest
from services.audit_service import log_event
from services.google_fit_service import (
    GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS,
    GoogleFitService,
)
from workers.google_fit_tasks import sync_google_fit_for_user_task

router = APIRouter(prefix="/api/v1/google-fit", tags=["Google Fit"])
integration_router = APIRouter(prefix="/api/v1/integrations/google-fit", tags=["Google Fit"])
wearable_router = APIRouter(prefix="/api/v1/wearable/google-fit", tags=["Google Fit"])


@router.get("/status")
def google_fit_status(
    timezone: str | None = Query(default=None),
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": GoogleFitService.get_status(db, current_user, timezone_name=timezone),
    }


@router.get("/debug")
async def google_fit_debug(
    timezone: str | None = Query(default=None),
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": await GoogleFitService.debug_steps(db, current_user, timezone_name=timezone),
    }


route_logger = logging.getLogger("google_fit_routes")
_ACTIVE_SYNC_USERS: set[str] = set()


def _log_connect_payload(result: dict[str, object]) -> None:
    route_logger.info(
        "[GFit] OAuth payload | client_id=%s | redirect_uri=%s | scopes=%s | state=%s | oauth_state=%s | auth_url=%s",
        result.get("client_id"),
        result.get("redirect_uri"),
        result.get("scopes"),
        result.get("state"),
        result.get("oauth_state"),
        result.get("auth_url"),
    )


def _build_oauth_error_redirect(default_redirect: str, message: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{default_redirect}?{urlencode({'googleFit': 'error', 'message': message})}",
        status_code=302,
    )


def _safe_not_connected_sync_result(db: Session, current_user, timezone: str | None = None) -> dict[str, object]:
    status_payload = GoogleFitService.get_status(db, current_user, timezone_name=timezone)
    return {
        "status": "not_connected",
        "lastUpdated": None,
        "data": {
            "success": True,
            "status": "not_connected",
            "error": None,
            "partial": True,
            "message": "Google Fit is not connected",
            "connected": False,
            "data": [],
            "stats": status_payload.get("stats", {}),
            "raw_json": status_payload.get("raw_json"),
            "google_email": status_payload.get("google_email"),
            "last_synced_at": status_payload.get("last_synced_at"),
            "last_sync_status": "disconnected",
            "timezone": status_payload.get("timezone"),
            "data_availability": status_payload.get("data_availability"),
            "scope_status": status_payload.get("scope_status"),
            "missing_scopes": status_payload.get("missing_scopes"),
            "needs_reconsent": status_payload.get("needs_reconsent"),
        },
    }


def _recent_sync_exists(db: Session, current_user, *, last_30_seconds: bool = False) -> dict[str, object] | None:
    window_seconds = 30 if last_30_seconds else 180
    connection = GoogleFitService.get_connection(db, current_user)
    if not connection:
        return None

    recent_background_sync = GoogleFitService.get_recent_background_sync(
        db,
        current_user,
        max_age_seconds=window_seconds,
    )
    if recent_background_sync:
        return {
            "reason": "background_sync_running",
            "task_id": recent_background_sync.get("task_id"),
            "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
        }

    if not connection.last_synced_at:
        return None

    last_synced_at = connection.last_synced_at
    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)

    seconds_since_sync = (datetime.now(timezone.utc) - last_synced_at).total_seconds()
    if seconds_since_sync <= window_seconds:
        return {
            "reason": "recent_sync",
            "seconds_since_sync": seconds_since_sync,
            "last_synced_at": connection.last_synced_at.isoformat(),
        }

    return None


def _build_duplicate_sync_result(db: Session, current_user, payload: GoogleFitSyncRequest, duplicate: dict[str, object]) -> dict[str, object]:
    status_data = GoogleFitService.get_status(db, current_user, timezone_name=payload.timezone)
    return {
        "success": True,
        "status": "skipped_duplicate",
        "error": None,
        "partial": False,
        "message": "Google Fit sync skipped because a sync ran recently.",
        "connected": status_data.get("connected", True),
        "sync_mode": "duplicate_guard",
        "duplicate": True,
        "duplicate_reason": duplicate.get("reason"),
        "task_id": duplicate.get("task_id"),
        "timezone": status_data.get("timezone"),
        "last_synced_at": status_data.get("last_synced_at") or duplicate.get("last_synced_at"),
        "last_sync_status": status_data.get("last_sync_status"),
        "stats": status_data.get("stats", GoogleFitService._build_stats([])),
        "raw_json": status_data.get("raw_json"),
        "google_email": status_data.get("google_email"),
        "data_availability": status_data.get("data_availability"),
        "scope_status": status_data.get("scope_status"),
        "missing_scopes": status_data.get("missing_scopes") or [],
        "needs_reconsent": status_data.get("needs_reconsent", False),
        "data": [],
    }


def _mark_google_fit_enqueue_failed(db: Session, current_user, task_id: str, error: Exception) -> None:
    connection = GoogleFitService.get_connection(db, current_user)
    if not connection:
        return

    raw_payload = GoogleFitService._connection_raw_payload(connection)
    background_sync = raw_payload.get("background_sync") if isinstance(raw_payload, dict) else None
    if isinstance(background_sync, dict):
        background_sync.update({"task_id": task_id, "status": "failed", "error": str(error)})
        raw_payload["background_sync"] = background_sync
    connection.last_sync_status = "failed"
    connection.raw_last_response = raw_payload
    db.add(connection)
    db.commit()


def _enqueue_google_fit_sync(
    db: Session,
    current_user,
    *,
    timezone: str | None,
    days: int,
) -> dict[str, object]:
    recent_sync = GoogleFitService.get_recent_background_sync(db, current_user)
    if recent_sync:
        return GoogleFitService.build_background_sync_response(
            db,
            current_user,
            timezone_name=timezone,
            days=days,
            task_id=recent_sync.get("task_id"),
            already_running=True,
        )

    task_id = str(uuid.uuid4())
    GoogleFitService.mark_background_sync_queued(
        db,
        current_user,
        task_id=task_id,
        timezone_name=timezone,
        days=days,
    )
    try:
        sync_google_fit_for_user_task.apply_async(
            kwargs={
                "user_id": str(current_user.id),
                "timezone_name": timezone,
                "days": days,
            },
            task_id=task_id,
        )
    except Exception as exc:
        _mark_google_fit_enqueue_failed(db, current_user, task_id, exc)
        route_logger.exception("[GFit] Failed to enqueue background sync | user=%s | task_id=%s", current_user.id, task_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Fit background sync queue is unavailable. Please retry shortly.",
        ) from exc

    return GoogleFitService.build_background_sync_response(
        db,
        current_user,
        timezone_name=timezone,
        days=days,
        task_id=task_id,
    )


@router.get("/connect")
def connect_google_fit(
    timezone: str | None = Query(default=None),
    redirect_path: str | None = Query(default="/device-settings/google-fit"),
    current_user=Depends(get_current_user_from_header),
):
    route_logger.info(
        f"[GFit] connect called | user={current_user.email} "
        f"| timezone={timezone!r} | redirect_path={redirect_path!r}"
    )
    try:
        result = GoogleFitService.build_connect_url(
            current_user,
            timezone_name=timezone,
            redirect_path=redirect_path,
            onboarding_step=4,
        )
        _log_connect_payload(result)
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": result,
        }
    except Exception as exc:
        import traceback

        route_logger.error(f"[GFit] connect ERROR: {exc}\n{traceback.format_exc()}")
        raise


@router.post("/connect/start")
def start_google_fit_connect(
    payload: GoogleFitConnectRequest,
    current_user=Depends(get_current_user_from_header),
):
    route_logger.info(
        f"[GFit] connect/start called | user={current_user.email} "
        f"| timezone={payload.timezone!r} | redirect_path={payload.redirect_path!r}"
    )
    try:
        result = GoogleFitService.build_connect_url(
            current_user,
            timezone_name=payload.timezone,
            redirect_path=payload.redirect_path,
        )
        _log_connect_payload(result)
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": result,
        }
    except Exception as exc:
        import traceback
        route_logger.error(f"[GFit] connect/start ERROR: {exc}\n{traceback.format_exc()}")
        raise


@integration_router.get("/url")
def get_google_fit_url(
    timezone: str | None = Query(default=None),
    redirect_path: str | None = Query(default="/devices"),
    current_user=Depends(get_current_user_from_header),
):
    result = GoogleFitService.build_connect_url(
        current_user,
        timezone_name=timezone,
        redirect_path=redirect_path,
    )
    _log_connect_payload(result)
    return result


logger = logging.getLogger("google_fit_routes")


@router.get("/oauth/callback")
async def google_fit_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    logger.info(
        f"[GFit] Callback received | error={error!r} "
        f"| code_len={len(code) if code else 0} "
        f"| code_preview={repr(code[:40]) if code else None} "
        f"| state_present={bool(state)}"
    )
    default_redirect = f"{settings.FRONTEND_APP_URL.rstrip('/')}/device-settings/google-fit"

    if error:
        return _build_oauth_error_redirect(default_redirect, error)

    if not code or not state:
        return _build_oauth_error_redirect(default_redirect, "missing_callback_parameters")

    try:
        redirect_url = await GoogleFitService.handle_callback(db, code=code, state_token=state)
    except HTTPException as exc:
        logger.error(f"[GFit] Callback handle_callback raised: {exc.detail}")
        redirect_url = f"{default_redirect}?{urlencode({'googleFit': 'error', 'message': str(exc.detail)})}"

    return RedirectResponse(url=redirect_url, status_code=302)


@integration_router.get("/callback")
async def google_fit_callback_compat(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    return await google_fit_callback(code=code, state=state, error=error, db=db)


async def _run_google_fit_data_sync(
    request: Request,
    response: Response,
    current_user,
    db: Session,
    endpoint: str,
) -> dict[str, object] | Response:
    connection, _access_token, blocked_result = await GoogleFitService.validate_sync_auth(
        db,
        current_user,
        timezone_name=None,
        sync_mode="data_sync",
    )
    if blocked_result is not None:
        result = {"status": blocked_result.get("status", "auth_blocked"), "lastUpdated": None, "data": blocked_result}
        log_event(
            current_user.id,
            "wearable_sync",
            endpoint,
            {
                "status": result.get("status"),
                "connected": blocked_result.get("connected"),
                "message": blocked_result.get("message"),
                "sync_blocked_reason": blocked_result.get("sync_blocked_reason"),
            },
        )
        return result

    if connection and connection.last_synced_at:
        route_logger.info("[GFit] Bypassing conditional cache for sync request | user=%s", current_user.id)

    sync_user_key = str(current_user.id)
    if GoogleFitService.is_sync_locked(sync_user_key):
        route_logger.info("SYNC_SKIPPED_LOCK | user=%s | source=data_sync", current_user.id)
        result = GoogleFitService.build_background_sync_response(
            db,
            current_user,
            timezone_name=connection.default_timezone if connection else None,
            days=GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
            already_running=True,
        )
    elif not GoogleFitService.acquire_sync_rate_limit(sync_user_key):
        route_logger.info("SYNC_SKIPPED_RATE_LIMIT | user=%s | source=data_sync", current_user.id)
        result = _build_duplicate_sync_result(
            db,
            current_user,
            GoogleFitSyncRequest(timezone=connection.default_timezone if connection else None, days=GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS),
            {"reason": "rate_limited", "last_synced_at": connection.last_synced_at.isoformat() if connection and connection.last_synced_at else None},
        )
    else:
        result = _enqueue_google_fit_sync(
            db,
            current_user,
            timezone=connection.default_timezone if connection else None,
            days=GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        )

    connection = GoogleFitService.get_connection(db, current_user)
    last_updated = None
    if connection and connection.last_synced_at:
        from email.utils import format_datetime

        response.headers["Last-Modified"] = format_datetime(connection.last_synced_at)
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        last_updated = connection.last_synced_at.isoformat()

    payload = {"status": result.get("status", "fresh"), "lastUpdated": last_updated, "data": result}
    log_event(
        current_user.id,
        "wearable_sync",
        endpoint,
        {
            "status": payload.get("status"),
            "connected": result.get("connected"),
            "partial": result.get("partial"),
            "records_synced": 0,
            "sync_mode": result.get("sync_mode"),
            "task_id": result.get("task_id"),
            "last_synced_at": result.get("last_synced_at"),
            "missing_scopes": result.get("missing_scopes") or [],
        },
    )
    return payload


@router.get("/data-sync")
async def fetch_data(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db)
):
    return await _run_google_fit_data_sync(request, response, current_user, db, "/api/v1/google-fit/data-sync")


@wearable_router.get("/data")
async def fetch_google_fit_wearable_data(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await _run_google_fit_data_sync(request, response, current_user, db, "/api/v1/wearable/google-fit/data")


@router.post("/sync")
async def sync_google_fit(
    payload: GoogleFitSyncRequest,
    silent: bool = Query(default=False),
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    connection, _access_token, blocked_result = await GoogleFitService.validate_sync_auth(
        db,
        current_user,
        timezone_name=payload.timezone,
        sync_mode="manual_api",
    )
    if blocked_result is not None:
        result = blocked_result
        log_event(
            current_user.id,
            "wearable_sync",
            "/api/v1/google-fit/sync",
            {
                "status": result.get("status"),
                "connected": result.get("connected"),
                "timezone": payload.timezone,
                "days": payload.days,
                "silent": silent,
                "sync_blocked_reason": result.get("sync_blocked_reason"),
            },
        )
        return result

    duplicate_sync = _recent_sync_exists(db, current_user, last_30_seconds=True)
    if duplicate_sync:
        result = _build_duplicate_sync_result(db, current_user, payload, duplicate_sync)
        log_event(
            current_user.id,
            "wearable_sync",
            "/api/v1/google-fit/sync",
            {
                "status": result.get("status"),
                "connected": result.get("connected"),
                "timezone": payload.timezone,
                "days": payload.days,
                "silent": silent,
                "duplicate": True,
                "duplicate_reason": result.get("duplicate_reason"),
                "last_synced_at": result.get("last_synced_at"),
            },
        )
        return result

    sync_user_key = str(current_user.id)
    if sync_user_key in _ACTIVE_SYNC_USERS:
        duplicate_sync = {"reason": "sync_in_progress"}
        result = _build_duplicate_sync_result(db, current_user, payload, duplicate_sync)
        log_event(
            current_user.id,
            "wearable_sync",
            "/api/v1/google-fit/sync",
            {
                "status": result.get("status"),
                "connected": result.get("connected"),
                "timezone": payload.timezone,
                "days": payload.days,
                "silent": silent,
                "duplicate": True,
                "duplicate_reason": result.get("duplicate_reason"),
            },
        )
        return result

    _ACTIVE_SYNC_USERS.add(sync_user_key)
    redis_lock_acquired = False
    try:
        try:
            requested_days = int(payload.days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS)
        except (TypeError, ValueError):
            requested_days = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS
        sync_days = max(1, min(requested_days, GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))

        if not GoogleFitService.acquire_sync_rate_limit(sync_user_key):
            route_logger.info("SYNC_SKIPPED_RATE_LIMIT | user=%s | source=manual_api", current_user.id)
            duplicate_sync = {
                "reason": "rate_limited",
                "last_synced_at": connection.last_synced_at.isoformat() if connection and connection.last_synced_at else None,
            }
            result = _build_duplicate_sync_result(db, current_user, payload, duplicate_sync)
            log_event(
                current_user.id,
                "wearable_sync",
                "/api/v1/google-fit/sync",
                {
                    "status": result.get("status"),
                    "duplicate": True,
                    "duplicate_reason": "rate_limited",
                },
            )
            return result

        # ── DISTRIBUTED LOCK ───────────────────────────────────
        redis_lock_acquired = GoogleFitService.acquire_sync_lock(sync_user_key)
        if not redis_lock_acquired:
            route_logger.info("SYNC_SKIPPED_LOCK | user=%s | source=manual_api", current_user.id)
            duplicate_sync = {"reason": "redis_lock_held"}
            result = _build_duplicate_sync_result(db, current_user, payload, duplicate_sync)
            log_event(
                current_user.id,
                "wearable_sync",
                "/api/v1/google-fit/sync",
                {
                    "status": result.get("status"),
                    "duplicate": True,
                    "duplicate_reason": "redis_lock_held",
                },
            )
            return result

        route_logger.info("SYNC_START | user=%s | source=manual_api | days=%s", current_user.id, sync_days)
        try:
            result = await GoogleFitService.sync_steps(
                db,
                current_user,
                timezone_name=payload.timezone,
                days=sync_days,
                silent=False,
            )
        except Exception as exc:
            db.rollback()
            route_logger.exception("[GFit] Direct sync isolated external failure | user=%s | error=%s", current_user.id, exc)
            result = GoogleFitService.build_fault_tolerant_sync_failure_response(
                db,
                current_user,
                exc,
                timezone_name=payload.timezone,
                retry_count=0,
                operation="api_sync",
                fallback_used=True,
            )
    finally:
        if redis_lock_acquired:
            GoogleFitService.release_sync_lock(sync_user_key)
        _ACTIVE_SYNC_USERS.discard(sync_user_key)

    log_event(
        current_user.id,
        "wearable_sync",
        "/api/v1/google-fit/sync",
        {
            "status": result.get("status"),
            "connected": result.get("connected"),
            "partial": result.get("partial"),
            "timezone": payload.timezone,
            "days": sync_days,
            "silent": silent,
            "records_synced": len(result.get("data") or []),
            "sync_mode": result.get("sync_mode"),
            "last_synced_at": result.get("last_synced_at"),
        },
    )
    return result


@router.delete("/disconnect")
def disconnect_google_fit(
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": GoogleFitService.disconnect(db, current_user),
    }
