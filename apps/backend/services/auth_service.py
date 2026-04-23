import uuid
import secrets
import logging
from functools import lru_cache
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import jwt
from jwt import algorithms
import requests
import json

from models import User, UserProfile, UserSetting, Session as DBSession
from schemas.api_models import OAuthLoginRequest, UserCreate, UserLogin, TokenResponse
from core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from core.config import settings
from core.utils import safe_input
from services.event_service import emit_event
from services.user_service import UserService

logger = logging.getLogger("auth_service")




class AuthService:
    @staticmethod
    def _issue_session(db: Session, user: User) -> tuple[str, str, datetime]:
        access_token = create_access_token(subject=user.id)
        refresh_token, refresh_expire = create_refresh_token(subject=user.id)

        session = DBSession(
            user_id=user.id,
            refresh_token_hash=get_password_hash(refresh_token),
            expires_at=refresh_expire,
        )
        db.add(session)
        db.commit()

        return access_token, refresh_token, refresh_expire

    @staticmethod
    def _ensure_user_profile_and_settings(db: Session, user: User, full_name: str | None = None) -> None:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if not profile:
            profile = UserProfile(
                user_id=user.id,
                full_name=safe_input(full_name) if full_name else user.full_name,
            )
            db.add(profile)
        elif full_name and not profile.full_name:
            profile.full_name = safe_input(full_name)

        setting = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
        if not setting:
            db.add(
                UserSetting(
                    user_id=user.id,
                    auto_fetch_enabled=False,
                    fetch_interval_minutes=15,
                )
            )

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_onboarding_done": user.is_onboarding_done,
            "onboarding_step": user.onboarding_step,
            "is_email_verified": user.is_email_verified,
            "gmail_connected": bool(getattr(user, "gmail_connected", False)),
            "apple_connected": bool(getattr(user, "apple_connected", False)),
            "has_password": user.password_hash != "OAUTH_NO_PASSWORD",
        }

    @staticmethod
    def _decode_supabase_token(token: str) -> dict:
        # ── Diagnostic logging — always visible in docker logs ───────────────
        supabase_url = settings.SUPABASE_URL or ''
        audience = settings.SUPABASE_AUDIENCE or ''
        token_preview = f"{token[:12]}...{token[-8:]}" if len(token) > 20 else token
        print(f"[Auth] SUPABASE_URL='{supabase_url}'")
        print(f"[Auth] SUPABASE_AUDIENCE='{audience}'")
        print(f"[Auth] Decoding token: {token_preview}")

        if not supabase_url:
            print("[Auth] ERROR: SUPABASE_URL is empty — set it in your .env file")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase OAuth is not configured (SUPABASE_URL missing)",
            )

        try:
            jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            print(f"NEW JWKS URL: {jwks_url}")
            
            headers = {}
            if settings.SUPABASE_ANON_KEY:
                headers["apikey"] = settings.SUPABASE_ANON_KEY
                
            response = requests.get(jwks_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print("JWKS fetch failed:", response.text)
                raise HTTPException(401, "Failed to fetch JWKS")
                
            jwks = response.json()
            
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get("alg", "RS256")
            kid = unverified_header.get("kid")
            print("JWT ALG:", alg)
            print("JWT KID:", kid)
            
            matching_key = next(
                (k for k in jwks.get("keys", []) if k.get("kid") == kid),
                None
            )
            if not matching_key:
                raise HTTPException(401, "JWK not found")

            print("Using key type:", matching_key.get("kty"))
            
            # Dynamically choose RSA or EC key based on token header alg
            if alg.startswith("RS"):
                public_key = algorithms.RSAAlgorithm.from_jwk(json.dumps(matching_key))
            elif alg.startswith("ES"):
                public_key = algorithms.ECAlgorithm.from_jwk(json.dumps(matching_key))
            else:
                raise HTTPException(401, f"Unsupported algorithm: {alg}")

            issuer = f"{supabase_url.rstrip('/')}/auth/v1"
            print(f"[Auth] Verifying with issuer='{issuer}' audience='{audience}' alg={alg}")
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=[alg],
                audience=audience,
                issuer=issuer,
            )
            print(f"[Auth] Token decoded OK — sub={decoded.get('sub')} email={decoded.get('email')}")
            print("JWT decoded successfully")
        except HTTPException:
            raise
        except jwt.PyJWTError as exc:
            print("JWT ERROR:", str(exc))
            print(f"[Auth] PyJWTError ({type(exc).__name__}): {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Supabase OAuth token: {exc}",
            ) from exc
        except Exception as exc:
            print("JWT ERROR:", str(exc))
            print(f"[Auth] Exception ({type(exc).__name__}): {exc}")
            logger.exception("[Auth] Failed to decode Supabase OAuth token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Supabase OAuth token: {exc}",
            ) from exc

        return decoded

    @staticmethod
    def oauth_login(db: Session, oauth_data: OAuthLoginRequest) -> dict:
        decoded = AuthService._decode_supabase_token(oauth_data.access_token)

        provider = str(
            oauth_data.provider
            or decoded.get("app_metadata", {}).get("provider")
            or ""
        ).strip().lower()

        token_provider = str(decoded.get("app_metadata", {}).get("provider") or "").strip().lower()
        if token_provider and provider and token_provider != provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth provider mismatch",
            )

        if provider not in {"google", "apple"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider",
            )

        email = str(decoded.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth token did not include an email address",
            )

        metadata = decoded.get("user_metadata") or {}
        full_name = (
            metadata.get("full_name")
            or metadata.get("name")
            or decoded.get("name")
        )

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_deleted = False
            user.is_email_verified = True
            if full_name and not user.full_name:
                user.full_name = safe_input(full_name)
        else:
            user = User(
                email=email,
                password_hash="OAUTH_NO_PASSWORD",
                full_name=safe_input(full_name) if full_name else None,
                is_email_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if provider == "google":
            user.gmail_connected = True
        elif provider == "apple":
            user.apple_connected = True

        AuthService._ensure_user_profile_and_settings(db, user, full_name=full_name)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        try:
            emit_event("USER_LOGIN", user.id, {"email": user.email, "provider": provider})
        except Exception:
            logger.exception("[Auth] Failed to emit oauth login notification for user=%s", user.id)

        access_token, refresh_token, _ = AuthService._issue_session(db, user)

        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": AuthService._serialize_user(user),
            },
        }

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


        access_token, refresh_token, _ = AuthService._issue_session(db, new_user)

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
        
        access_token, refresh_token, _ = AuthService._issue_session(db, user)
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
            
        user = db.query(User).filter(User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id).first()
        new_access_token = create_access_token(subject=user_id)
        
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "access_token": new_access_token,
                "refresh_token": old_refresh_token,
                "token_type": "bearer",
                "user": AuthService._serialize_user(user)
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

    @staticmethod
    def update_password(db: Session, user_id: str, current_password: str | None, new_password: str) -> dict:
        from core.security import validate_password, get_password_hash, verify_password
        
        if not validate_password(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain at least one uppercase letter, one number, and one special character."
            )
            
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            User.is_deleted == False
        ).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Require current password if it's a standard user who didn't sign up strictly via OAuth
        # Check OAuth status: if they have gmail/apple connected AND no current_password provided, we allow it.
        # But if they provide current_password we always check it.
        if current_password:
            if not verify_password(current_password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password")
        else:
            if not getattr(user, 'gmail_connected', False) and not getattr(user, 'apple_connected', False):
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is required")

        user.password_hash = get_password_hash(new_password)
        db.commit()
        return {"success": True, "status": "ready", "data": {"message": "Password updated successfully"}}
