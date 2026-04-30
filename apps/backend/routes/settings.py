from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import NotificationPreferencesUpdate
from services.notification_preferences_service import NotificationPreferencesService
from services.notification_service import trigger_notification

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


@router.get("/notifications")
def get_notification_preferences(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationPreferencesService.get_preferences(db, current_user)


@router.put("/notifications")
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return NotificationPreferencesService.update_preferences(db, current_user, payload.model_dump(exclude_unset=True))


@router.post("/test-notification")
async def send_test_notification(
    payload: dict | None = Body(default=None),
    current_user: User = Depends(get_current_user_from_header),
):
    request_payload = dict(payload or {})
    return await trigger_notification(
        user_id=str(current_user.id),
        event_type=str(request_payload.get("event_type") or "system"),
        title=str(request_payload.get("title") or "Test notification"),
        message=str(request_payload.get("message") or "ArogyaAI notification delivery test completed."),
        data={
            "url": request_payload.get("url") or "/notifications",
            "summary": request_payload.get("summary") or "Manual notification pipeline validation.",
            "severity": request_payload.get("severity") or "info",
            "test": True,
        },
    )
