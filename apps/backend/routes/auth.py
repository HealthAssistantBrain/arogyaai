from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Body
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from schemas.api_models import OAuthLoginRequest, UserLogin, UserCreate, PasswordUpdate
from core.session_cookies import clear_session_cookies
from services.auth_service import AuthService
from services.audit_service import log_event
from services.onboarding_service import OnboardingService
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Legacy custom signup is disabled. Use Supabase Auth signUp from the frontend."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Custom signup is disabled. Use Supabase Auth.",
    )

@router.post("/login")
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Legacy custom login is disabled. Use Supabase Auth signInWithPassword from the frontend."""
    log_event(
        None,
        "login",
        "/api/v1/auth/login",
        {
            "status": "disabled",
            "reason": "legacy_custom_login_disabled",
            "email": user_data.email,
        },
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Custom login is disabled. Use Supabase Auth.",
    )


@router.post("/oauth")
async def oauth_login(oauth_data: OAuthLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Legacy Supabase-to-backend JWT exchange is disabled. Send Supabase JWTs directly."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="OAuth exchange is disabled. Send the Supabase access token as the bearer token.",
    )

@router.post("/refresh")
@router.post("/refresh-token")
async def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Legacy custom refresh is disabled. Supabase refreshes browser sessions automatically."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Custom token refresh is disabled. Use Supabase Auth session refresh.",
    )

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Clear legacy backend cookies. Supabase sign-out happens on the frontend."""
    clear_session_cookies(response)
    return {"success": True, "status": "ready", "data": {"message": "Session cleared"}}

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """
    Mark the authenticated user's email as verified via AuthService.
    """
    return AuthService.verify_email(db, current_user.id)

@router.post("/complete-onboarding", status_code=status.HTTP_200_OK)
async def complete_onboarding(
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Finalize onboarding through the auth namespace for frontend auth flows."""
    return OnboardingService.finalize_onboarding(db, current_user, payload)

@router.put("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Legacy backend password update is disabled. Use Supabase Auth updateUser."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Password updates are handled by Supabase Auth.",
    )
