import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from database.session import get_db
from routes.users import get_current_user_from_header
from schemas.api_models import GoogleFitConnectRequest, GoogleFitSyncRequest
from services.google_fit_service import GoogleFitService

router = APIRouter(prefix="/api/v1/google-fit", tags=["Google Fit"])


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
        return RedirectResponse(
            url=f"{default_redirect}?{urlencode({'googleFit': 'error', 'message': error})}",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{default_redirect}?{urlencode({'googleFit': 'error', 'message': 'missing_callback_parameters'})}",
            status_code=302,
        )

    try:
        redirect_url = await GoogleFitService.handle_callback(db, code=code, state_token=state)
    except HTTPException as exc:
        logger.error(f"[GFit] Callback handle_callback raised: {exc.detail}")
        redirect_url = f"{default_redirect}?{urlencode({'googleFit': 'error', 'message': str(exc.detail)})}"

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/sync")
async def sync_google_fit(
    payload: GoogleFitSyncRequest,
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": await GoogleFitService.sync_steps(
            db,
            current_user,
            timezone_name=payload.timezone,
            days=payload.days,
        ),
    }


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
