from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User, UserProfile
from models.user import ROLE_DOCTOR
from services.auth_service import AuthService
from services.user_service import UserService


def _get_bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def get_supabase_claims_from_header(
    authorization: str | None = Header(default=None),
) -> dict:
    token = _get_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = AuthService._decode_supabase_token(token)
    return {**claims, "auth_provider": "supabase"}


def get_current_user_from_header(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
) -> User:
    return AuthService.get_or_create_user_from_supabase_claims(db, claims)


def get_existing_user_from_header(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
) -> User:
    user = AuthService.get_user_from_supabase_claims(db, claims)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user has not been synchronized yet",
        )
    return user


def get_current_doctor_from_header(
    current_user: User = Depends(get_current_user_from_header),
) -> User:
    if (getattr(current_user, "role", "") or "").lower() != ROLE_DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor role required",
        )
    return current_user


def get_current_user_profile(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
) -> UserProfile:
    return UserService.get_or_create_user_profile(db, current_user)


def get_current_user(
    current_profile: UserProfile = Depends(get_current_user_profile),
) -> UserProfile:
    return current_profile
