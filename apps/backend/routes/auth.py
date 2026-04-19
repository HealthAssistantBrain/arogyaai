from fastapi import APIRouter, Depends, HTTPException, status, Response, Header
from sqlalchemy.orm import Session
import jwt

from database.session import get_db
from models import User
from schemas.api_models import OAuthLoginRequest, UserLogin, UserCreate, TokenResponse, RefreshTokenRequest
from core.security import create_access_token
from core.config import settings
from services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user account via AuthService."""
    result = AuthService.signup(db, user_data)
    
    # Set CSRF Cookie for frontend security
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token", 
        value=csrf_token, 
        httponly=False,
        samesite="lax",
        secure=False
    )
    
    return result

@router.post("/login")
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate via AuthService."""
    result = AuthService.login(db, user_data)
    
    # CSRF Cookie
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token", 
        value=csrf_token, 
        httponly=False,
        samesite="lax",
        secure=False
    )
    
    return result


@router.post("/oauth")
async def oauth_login(oauth_data: OAuthLoginRequest, db: Session = Depends(get_db)):
    """Exchange a Supabase OAuth token for a backend-issued JWT session."""
    token_preview = (
        f"{oauth_data.access_token[:12]}...{oauth_data.access_token[-8:]}"
        if len(oauth_data.access_token) > 20 else oauth_data.access_token
    )
    print(f"[OAuth Route] provider={oauth_data.provider!r} token={token_preview}")
    return AuthService.oauth_login(db, oauth_data)

@router.post("/refresh-token")
async def refresh_access_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Validate and issue fresh token via AuthService."""
    try:
        payload = jwt.decode(data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if token_type != "refresh" or not user_id:
            raise ValueError()
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid"
        )
        
    return AuthService.refresh_token(db, user_id, data.refresh_token)

@router.post("/logout")
async def logout(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Revoke session via AuthService."""
    try:
        payload = jwt.decode(data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        return {"success": True, "status": "ready", "data": {"message": "Session revoked"}}
        
    return AuthService.logout(db, user_id, data.refresh_token)


from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Mark the authenticated user's email as verified via AuthService.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "access":
             raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return AuthService.verify_email(db, user_id)
