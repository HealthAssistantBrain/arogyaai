import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import User, Session as DBSession

class UserService:
    @staticmethod
    def get_user_me(user: User) -> dict:
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "id":                  str(user.id),
                "email":               user.email,
                "full_name":           user.full_name,
                "is_email_verified":   user.is_email_verified,
                "is_onboarding_done":  user.is_onboarding_done,
                "onboarding_step":     user.onboarding_step,
                "health_score":        float(user.health_score) if user.health_score is not None else 0.0,
                "score_change":        float(user.score_change_percent) if user.score_change_percent is not None else 0.0,
                "role":                "user",
                "created_at":          user.created_at.isoformat() if user.created_at else None,
            }
        }

    @staticmethod
    def update_user_me(db: Session, user: User, updates: dict) -> dict:
        allowed_fields = {"full_name", "is_onboarding_done", "onboarding_step"}
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "message": "Profile updated",
                "id": str(user.id),
                "user": {
                    "is_onboarding_done": user.is_onboarding_done,
                    "onboarding_step": user.onboarding_step
                }
            }
        }

    @staticmethod
    def delete_user_me(db: Session, user: User) -> dict:
        # 1. Soft-delete user
        user.is_deleted = True
        user.updated_at = datetime.now(timezone.utc)
        
        # 2. Revoke all active sessions
        db.query(DBSession).filter(
            DBSession.user_id == user.id,
            DBSession.is_revoked == False
        ).update({"is_revoked": True}, synchronize_session='fetch')

        db.commit()
        return {"success": True, "status": "ready", "error": None, "data": {"message": "Account deactivated"}}
