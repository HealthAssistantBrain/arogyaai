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


@router.post("/connect/start")
def start_google_fit_connect(
    payload: GoogleFitConnectRequest,
    current_user=Depends(get_current_user_from_header),
):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": GoogleFitService.build_connect_url(
            current_user,
            timezone_name=payload.timezone,
            redirect_path=payload.redirect_path,
        ),
    }


@router.get("/oauth/callback")
async def google_fit_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
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
