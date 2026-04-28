import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from database.session import get_db
from routes.users import get_current_user_from_header
from schemas.api_models import GoogleFitConnectRequest, GoogleFitSyncRequest
from services.google_fit_service import GoogleFitService

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


route_logger = logging.getLogger("google_fit_routes")


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
        },
    }


def _mark_google_fit_disconnected(db: Session, current_user) -> None:
    connection = GoogleFitService.get_connection(db, current_user)
    if not connection:
        return

    connection.last_sync_status = "disconnected"
    db.commit()


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
) -> dict[str, object] | Response:
    if not current_user.google_fit_connection:
        return _safe_not_connected_sync_result(db, current_user)

    connection = GoogleFitService.get_connection(db, current_user)

    if connection and connection.last_synced_at:
        current_etag = f'W/"{int(connection.last_synced_at.timestamp())}"'
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match == current_etag:
            return Response(status_code=304)

        if_modified_since = request.headers.get("If-Modified-Since")
        if if_modified_since:
            try:
                from email.utils import parsedate_to_datetime

                client_date = parsedate_to_datetime(if_modified_since)
                last_mod_floored = connection.last_synced_at.replace(microsecond=0)
                if last_mod_floored <= client_date:
                    return Response(status_code=304)
            except Exception:
                pass

    try:
        result = await GoogleFitService.sync_steps(
            db=db,
            user=current_user,
            days=1,
            silent=True,
        )
    except HTTPException as exc:
        if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            _mark_google_fit_disconnected(db, current_user)
            return _safe_not_connected_sync_result(db, current_user)
        raise

    connection = GoogleFitService.get_connection(db, current_user)
    last_updated = None
    if connection and connection.last_synced_at:
        from email.utils import format_datetime

        response.headers["Last-Modified"] = format_datetime(connection.last_synced_at)
        response.headers["ETag"] = f'W/"{int(connection.last_synced_at.timestamp())}"'
        response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
        last_updated = connection.last_synced_at.isoformat()

    return {"status": result.get("status", "fresh"), "lastUpdated": last_updated, "data": result}


@router.get("/data-sync")
async def fetch_data(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db)
):
    return await _run_google_fit_data_sync(request, response, current_user, db)


@wearable_router.get("/data")
async def fetch_google_fit_wearable_data(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await _run_google_fit_data_sync(request, response, current_user, db)


@router.post("/sync")
async def sync_google_fit(
    payload: GoogleFitSyncRequest,
    silent: bool = Query(default=False),
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    if not current_user.google_fit_connection:
        return _safe_not_connected_sync_result(db, current_user, payload.timezone)["data"]

    return await GoogleFitService.sync_steps(
        db,
        current_user,
        timezone_name=payload.timezone,
        days=payload.days,
        silent=silent,
    )


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
