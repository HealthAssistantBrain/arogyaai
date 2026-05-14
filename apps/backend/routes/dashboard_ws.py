from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from core.serialization.safe_response import websocket_send_json_safe
from database.session import SessionLocal
from models import User
from dashboard_realtime.connection_manager import dashboard_connection_manager
from services.auth_service import AuthService
from services.dashboard_realtime import cancel_dashboard_refresh, ensure_dashboard_snapshot_refresh, get_cached_realtime_payload

router = APIRouter(tags=["Dashboard Realtime"])


async def _authenticate_dashboard_socket(websocket: WebSocket, user_id: str) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        return None

    try:
        payload = await AuthService._decode_supabase_token(token)
    except Exception:
        return None

    token_user_id = payload.get("sub")
    if not token_user_id:
        return None

    db: Session = SessionLocal()
    try:
        user = AuthService.get_or_create_user_from_supabase_claims(db, payload)
        return user if str(user.id) == str(user_id) else None
    finally:
        db.close()


@router.websocket("/ws/dashboard/{user_id}")
async def dashboard_socket(websocket: WebSocket, user_id: str):
    current_user = await _authenticate_dashboard_socket(websocket, user_id)
    if not current_user:
        await websocket.close(code=1008)
        return

    session_id = await dashboard_connection_manager.connect(str(current_user.id), websocket)

    try:
        db: Session = SessionLocal()
        try:
            fresh_user = db.query(User).filter(User.id == current_user.id, User.is_deleted == False).first()
            if not fresh_user:
                await websocket.close(code=1008)
                return
        finally:
            db.close()

        initial_payload = await get_cached_realtime_payload(str(current_user.id), schedule_refresh=True)
        sent = await websocket_send_json_safe(
            websocket,
            {
                "type": "dashboard.update",
                "user_id": str(current_user.id),
                "data": initial_payload,
                "last_updated": initial_payload.get("last_updated"),
            },
            channel="dashboard.initial",
            context=f"dashboard.initial:{current_user.id}:{session_id}",
        )
        if not sent:
            return
        await dashboard_connection_manager.prime_snapshot(str(current_user.id), initial_payload, session_id=session_id)
        await ensure_dashboard_snapshot_refresh(str(current_user.id), reason="socket_connect")

        while True:
            message = await websocket.receive_text()
            await dashboard_connection_manager.mark_heartbeat(str(current_user.id), websocket, session_id=session_id)
            if message == "ping":
                sent = await websocket_send_json_safe(
                    websocket,
                    {
                        "type": "dashboard.pong",
                        "user_id": str(current_user.id),
                        "last_updated": initial_payload.get("last_updated"),
                    },
                    channel="dashboard.heartbeat",
                    context=f"dashboard.pong:{current_user.id}:{session_id}",
                )
                if not sent:
                    return
                continue
    except WebSocketDisconnect:
        pass
    finally:
        await dashboard_connection_manager.disconnect(str(current_user.id), websocket, session_id=session_id, reason="socket_closed")
        if not await dashboard_connection_manager.has_connection(str(current_user.id)):
            await cancel_dashboard_refresh(str(current_user.id))
