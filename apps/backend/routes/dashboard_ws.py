from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database.session import SessionLocal
from services.auth_service import AuthService
from services.dashboard_realtime import build_realtime_payload, dashboard_connection_manager

router = APIRouter(tags=["Dashboard Realtime"])


def _authenticate_dashboard_socket(websocket: WebSocket, user_id: str) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        return None

    try:
        payload = AuthService._decode_supabase_token(token)
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
    current_user = _authenticate_dashboard_socket(websocket, user_id)
    if not current_user:
        await websocket.close(code=1008)
        return

    await dashboard_connection_manager.connect(str(current_user.id), websocket)

    db: Session = SessionLocal()
    try:
        initial_payload = await build_realtime_payload(db, current_user)
        await websocket.send_json(
            {
                "type": "dashboard.update",
                "user_id": str(current_user.id),
                "data": initial_payload,
                "last_updated": initial_payload.get("last_updated"),
            }
        )

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await dashboard_connection_manager.disconnect(str(current_user.id), websocket)
        db.close()
