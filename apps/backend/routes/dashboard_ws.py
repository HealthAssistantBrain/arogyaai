from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from core.config import settings
from database.session import SessionLocal
from models import User
from services.dashboard_realtime import build_realtime_payload, dashboard_connection_manager

router = APIRouter(tags=["Dashboard Realtime"])


def _authenticate_dashboard_socket(websocket: WebSocket, user_id: str) -> User | None:
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None

    token_user_id = payload.get("sub")
    token_type = payload.get("type")
    if token_type != "access" or not token_user_id:
        return None

    try:
        requested_user_id = uuid.UUID(str(user_id))
        decoded_user_id = uuid.UUID(str(token_user_id))
    except (TypeError, ValueError):
        return None

    if requested_user_id != decoded_user_id:
        return None

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == requested_user_id, User.is_deleted == False).first()
        return user
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
