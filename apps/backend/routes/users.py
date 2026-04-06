"""
users.py — User routes

Exposes:
  GET /users/me       ← called by frontend hydrateAuth() on every boot
  PUT /users/me       ← profile update (stub)
  DELETE /users/me    ← account deletion (stub)
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header as FastAPIHeader
from sqlalchemy.orm import Session
import jwt

from database.session import get_db
from models import User
from core.config import settings
from services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

def get_current_user_from_header(
    authorization: str = FastAPIHeader(None),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(
        User.id == uuid.UUID(user_id),
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Returns the authenticated user's core profile data via UserService."""
    return UserService.get_user_me(db, current_user)


@router.put("/me")
def update_me(
    updates: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Update mutable profile fields via UserService."""
    return UserService.update_user_me(db, current_user, updates)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Deactivate user via UserService."""
    return UserService.delete_user_me(db, current_user)
