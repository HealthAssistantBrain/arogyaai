from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import jwt
import secrets
from datetime import datetime, timezone
from core.utils import safe_input

from database.session import get_db
from models import User, Session as DBSession
from schemas.api_models import UserLogin, UserCreate, TokenResponse, RefreshTokenRequest
from core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user account, hash the password, and issue JWT tokens."""
    # 1. Verification
    user_exists = db.query(User).filter(User.email == user_data.email).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # 2. Hashing & Creation
    print(f"DEBUG: Starting signup for {user_data.email}")
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_pwd,
        full_name=safe_input(user_data.full_name) if user_data.full_name else None
    )
    db.add(new_user)
    print("DEBUG: User added to session")
    db.commit()
    print("DEBUG: User committed")
    db.refresh(new_user)
    print(f"DEBUG: User refreshed, ID: {new_user.id}")

    # 3. Token Generation
    access_token = create_access_token(subject=new_user.id)
    refresh_token, refresh_expire = create_refresh_token(subject=new_user.id)
    
    # 4. Session Persistence
    print(f"DEBUG: Creating session for user ID {new_user.id}")
    session = DBSession(
        user_id=new_user.id,
        refresh_token_hash=get_password_hash(refresh_token), # Security Rule: Hash refresh token
        expires_at=refresh_expire
    )
    db.add(session)
    db.commit()
    print("DEBUG: Session committed, signup complete")

    # 5. CSRF Cookie (Requested for production-grade security flow)
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token", 
        value=csrf_token, 
        httponly=False,  # Allow frontend to read for double-submission if needed
        samesite="lax",
        secure=False     # Set true in production with HTTPS
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate via email/password, issue tokens, track session."""
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

    # CSRF Cookie
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token", 
        value=csrf_token, 
        httponly=False,
        samesite="lax",
        secure=False
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_access_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Validate refresh token and issue a fresh access token."""
    try:
        # 1. Decode generic payload ensuring expiry isn't tripped
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
        
    # 2. Database Session Check (Look up all active sessions for user, verify exact token match)
    active_sessions = db.query(DBSession).filter(
        DBSession.user_id == user_id, 
        DBSession.is_revoked == False,
        DBSession.expires_at > datetime.now(timezone.utc)
    ).all()
    
    valid_session = None
    for session in active_sessions:
        if verify_password(data.refresh_token, session.refresh_token_hash):
            valid_session = session
            break
            
    if not valid_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or session invalid"
        )
        
    # 3. Issue new Access Token (Leaving Refresh untouched as per standard)
    new_access_token = create_access_token(subject=user_id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=data.refresh_token,
        token_type="bearer"
    )

@router.post("/logout")
async def logout(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Log out by finding the targeted session via refresh token and revoking it."""
    try:
        payload = jwt.decode(data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        # Even if expired, gracefully accept the logout attempt
        return {"message": "Session revoked"}
        
    active_sessions = db.query(DBSession).filter(
        DBSession.user_id == user_id, 
        DBSession.is_revoked == False
    ).all()
    
    for session in active_sessions:
        if verify_password(data.refresh_token, session.refresh_token_hash):
            session.is_revoked = True
            db.commit()
            return {"message": "Session revoked successfully"}
            
    raise HTTPException(status_code=401, detail="Session not found or already revoked")
