import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
import jwt

from database.session import get_db
from models import User
from schemas.api_models import OAuthLoginRequest, UserLogin, UserCreate, TokenResponse, RefreshTokenRequest, PasswordUpdate
from core.security import create_access_token
from core.config import settings
from core.session_cookies import clear_session_cookies, set_session_cookies
from services.auth_service import AuthService
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user account via AuthService."""
    result = AuthService.signup(db, user_data)
    csrf_token = secrets.token_urlsafe(32)
    set_session_cookies(
        response,
        access_token=result["data"]["access_token"],
        refresh_token=result["data"].get("refresh_token"),
        csrf_token=csrf_token,
    )
    
    return result

@router.post("/login")
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate via AuthService."""
    result = AuthService.login(db, user_data)
    csrf_token = secrets.token_urlsafe(32)
    set_session_cookies(
        response,
        access_token=result["data"]["access_token"],
        refresh_token=result["data"].get("refresh_token"),
        csrf_token=csrf_token,
    )
    
    return result


@router.post("/oauth")
async def oauth_login(oauth_data: OAuthLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Exchange a Supabase OAuth token for a backend-issued JWT session."""
    token_preview = (
        f"{oauth_data.access_token[:12]}...{oauth_data.access_token[-8:]}"
        if len(oauth_data.access_token) > 20 else oauth_data.access_token
    )
    print(f"[OAuth Route] provider={oauth_data.provider!r} token={token_preview}")
    result = AuthService.oauth_login(db, oauth_data)
    csrf_token = secrets.token_urlsafe(32)
    set_session_cookies(
        response,
        access_token=result["data"]["access_token"],
        refresh_token=result["data"].get("refresh_token"),
        csrf_token=csrf_token,
    )
    return result

@router.post("/refresh")
@router.post("/refresh-token")
async def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Validate and issue fresh token via AuthService."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        # Try finding it in body for backward compatibility
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except:
            pass
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if token_type != "refresh" or not user_id:
            raise ValueError()
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid"
        )
        
    result = AuthService.refresh_token(db, user_id, refresh_token)
    set_session_cookies(
        response,
        access_token=result["data"]["access_token"],
        refresh_token=result["data"].get("refresh_token"),
    )
    return result

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Revoke session via AuthService."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except:
            pass
            
    if not refresh_token:
        clear_session_cookies(response)
        return {"success": True, "status": "ready", "data": {"message": "Session revoked"}}

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        clear_session_cookies(response)
        return {"success": True, "status": "ready", "data": {"message": "Session revoked"}}
        
    result = AuthService.logout(db, user_id, refresh_token)
    clear_session_cookies(response)
    return result

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """
    Mark the authenticated user's email as verified via AuthService.
    """
    return AuthService.verify_email(db, current_user.id)

@router.put("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    from core.security import get_password_hash
    hashed = get_password_hash(payload.password)

    user.password_hash = hashed
    db.commit()

    return {"message": "Password updated"}
