import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import User, UserProfile, UserSetting, Session as DBSession
from schemas.api_models import UserCreate, UserLogin, TokenResponse
from core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from core.utils import safe_input
from services.event_service import emit_event

logger = logging.getLogger("auth_service")

class AuthService:
    @staticmethod
    def signup(db: Session, user_data: UserCreate) -> dict:
        user_exists = db.query(User).filter(User.email == user_data.email).first()
        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        hashed_pwd = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_pwd,
            full_name=safe_input(user_data.full_name) if user_data.full_name else None
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        db.add(
            UserProfile(
                user_id=new_user.id,
                full_name=safe_input(user_data.full_name) if user_data.full_name else None,
            )
        )
        db.commit()

        db.add(
            UserSetting(
                user_id=new_user.id,
                auto_fetch_enabled=False,
                fetch_interval_minutes=15,
            )
        )
        db.commit()

        # ── Link Initial Profile if DOB provided ──
        if user_data.dob:
            from models import HealthProfile
            try:
                # Expecting YYYY-MM-DD
                dob_date = datetime.strptime(user_data.dob, "%Y-%m-%d").date()
                initial_profile = HealthProfile(
                    user_id=new_user.id,
                    date_of_birth=dob_date
                )
                db.add(initial_profile)
                db.commit()
            except Exception as profile_err:
                # Log error but don't crash signup
                print(f"Warning: Could not create profile during signup: {profile_err}")
                db.rollback() 


        access_token = create_access_token(subject=new_user.id)
        refresh_token, refresh_expire = create_refresh_token(subject=new_user.id)
        
        session = DBSession(
            user_id=new_user.id,
            refresh_token_hash=get_password_hash(refresh_token),
            expires_at=refresh_expire
        )
        db.add(session)
        db.commit()

        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(new_user.id),
                    "email": new_user.email,
                    "is_onboarding_done": new_user.is_onboarding_done
                }
            }
        }

    @staticmethod
    def login(db: Session, user_data: UserLogin) -> dict:
        user = db.query(User).filter(User.email == user_data.email, User.is_deleted == False).first()
        
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = create_access_token(subject=user.id)
        refresh_token, refresh_expire = create_refresh_token(subject=user.id)
        
        session = DBSession(
            user_id=user.id,
            refresh_token_hash=get_password_hash(refresh_token),
            expires_at=refresh_expire
        )
        db.add(session)
        db.commit()
        try:
            emit_event("USER_LOGIN", user.id, {"email": user.email})
        except Exception:
            logger.exception("[Auth] Failed to emit login notification for user=%s", user.id)
        
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "is_onboarding_done": user.is_onboarding_done
                }
            }
        }

    @staticmethod
    def refresh_token(db: Session, user_id: str, old_refresh_token: str) -> dict:
        # DB Session Check
        active_sessions = db.query(DBSession).filter(
            DBSession.user_id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id, 
            DBSession.is_revoked == False,
            DBSession.expires_at > datetime.now(timezone.utc)
        ).all()
        
        valid_session = None
        for session in active_sessions:
            if verify_password(old_refresh_token, session.refresh_token_hash):
                valid_session = session
                break
                
        if not valid_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or session invalid"
            )
            
        new_access_token = create_access_token(subject=user_id)
        
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "access_token": new_access_token,
                "refresh_token": old_refresh_token,
                "token_type": "bearer"
            }
        }

    @staticmethod
    def logout(db: Session, user_id: str, refresh_token: str) -> dict:
        active_sessions = db.query(DBSession).filter(
            DBSession.user_id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id, 
            DBSession.is_revoked == False
        ).all()
        
        for session in active_sessions:
            if verify_password(refresh_token, session.refresh_token_hash):
                session.is_revoked = True
                db.commit()
                return {"success": True, "status": "ready", "error": None, "data": {"message": "Session revoked successfully"}}
                
        raise HTTPException(status_code=401, detail="Session not found or already revoked")

    @staticmethod
    def verify_email(db: Session, user_id: str) -> dict:
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            User.is_deleted == False
        ).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.is_email_verified:
            return {"success": True, "status": "ready", "error": None, "data": {"message": "Email already verified", "is_email_verified": True}}

        user.is_email_verified = True
        db.commit()

        return {"success": True, "status": "ready", "error": None, "data": {"message": "Email verified successfully", "is_email_verified": True}}
