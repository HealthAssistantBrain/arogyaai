"""
users.py — User routes

Exposes:
  GET /users/me       ← called by frontend hydrateAuth() on every boot
  PUT /users/me       ← profile update (stub)
  DELETE /users/me    ← account deletion (stub)
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from database.session import get_db
from models import User
from core.config import settings

router = APIRouter(prefix="/users", tags=["Users"])

# ── JWT Bearer dependency ──────────────────────────────────────────────────────
def get_current_user(
    authorization: str = None,
    db: Session = Depends(get_db),
) -> User:
    """
    Parse the Authorization: Bearer <token> header, validate the JWT,
    pull the user from the DB, and return it.
    All guards forward here through FastAPI dependency injection.
    """
    raise HTTPException(status_code=401, detail="Not implemented — import from deps")


# Use a proper Header dependency
from fastapi import Header as FastAPIHeader

def get_current_user_from_header(
    authorization: str = FastAPIHeader(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token, validates JWT, and returns the DB User.
    Raises 401 for any failure.
    """
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
        User.is_deleted == False      # noqa: E712
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user_from_header)):
    """
    Returns the authenticated user's core profile data.
    The frontend `hydrateAuth()` calls this on every page load to sync Zustand.
    """
    return {
        "id":                  str(current_user.id),
        "email":               current_user.email,
        "full_name":           current_user.full_name,
        "is_email_verified":   current_user.is_email_verified,
        "is_onboarding_done":  current_user.is_onboarding_done,
        "role":                "user",
        "created_at":          current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/me")
def update_me(
    updates: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Update mutable profile fields (full_name, etc.)."""
    allowed_fields = {"full_name"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(current_user, field, value)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated", "id": str(current_user.id)}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Soft-delete the authenticated user."""
    current_user.is_deleted = True
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
