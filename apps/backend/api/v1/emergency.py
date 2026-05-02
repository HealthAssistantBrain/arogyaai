from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from models import User
from routes.users import get_current_user_from_header
from services.emergency_engine import detect_emergency_async

router = APIRouter(prefix="/api/v1/emergency", tags=["Emergency"])


@router.post("/check")
async def check_emergency(
    payload: dict[str, Any] | None = Body(default=None),
    current_user: User = Depends(get_current_user_from_header),
):
    request_payload = dict(payload or {})
    trigger_alerts = bool(request_payload.get("trigger_alerts", True))
    signal_overrides = request_payload.get("signals") if isinstance(request_payload.get("signals"), dict) else request_payload

    return await detect_emergency_async(
        current_user.id,
        signal_overrides=signal_overrides,
        trigger_alerts=trigger_alerts,
    )
