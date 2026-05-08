from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Body
from sqlalchemy.orm import Session

from core.config import settings
from database.session import get_db
from models import User
from schemas.api_models import OAuthLoginRequest, UserLogin, UserCreate, PasswordUpdate
from core.session_cookies import clear_session_cookies
from services.auth_service import AuthService
from services.onboarding_service import OnboardingService
from services.user_service import UserService
from services.google_fit_service import GoogleFitService
from routes.users import get_current_user_from_header, get_supabase_claims_from_header

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

LEGACY_AUTH_DEPRECATION_DETAIL = (
    "Backend-managed auth is deprecated. Use Supabase Auth on the frontend and send the Supabase access token as the bearer token."
)

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Legacy custom signup is disabled. Use Supabase Auth signUp from the frontend."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Custom signup is disabled. Use Supabase Auth.",
    )

@router.post("/login")
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Deprecated legacy email/password login. Supabase Auth is the only login authority."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=LEGACY_AUTH_DEPRECATION_DETAIL,
    )


@router.post("/oauth")
async def oauth_login(oauth_data: OAuthLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Legacy Supabase-to-backend JWT exchange is disabled. Send Supabase JWTs directly."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="OAuth exchange is disabled. Send the Supabase access token as the bearer token.",
    )


@router.post("/social-login")
async def social_login(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
):
    """Synchronize a Supabase OAuth user from the bearer JWT after browser login."""
    if claims.get("auth_provider") != "supabase":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user = AuthService.get_or_create_user_from_supabase_claims(db, claims)
    return UserService.get_user_me(db, current_user)

@router.post("/refresh")
@router.post("/refresh-token")
async def refresh_access_token(
    request: Request,
    response: Response,
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    """Deprecated backend refresh flow. Supabase Auth owns session refresh in the browser."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Backend refresh is deprecated. Refresh the Supabase session from the frontend client.",
    )

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Clear legacy backend cookies. Supabase sign-out happens on the frontend."""
    # Best-effort: cancel any active Google Fit sync for this user
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header:
            token = auth_header.replace("Bearer ", "").strip()
            if token:
                try:
                    claims = AuthService._decode_supabase_token(token)
                    current_user = AuthService.get_user_from_supabase_claims(db, claims)
                    if current_user:
                        GoogleFitService.stop_sync_on_logout(db, str(current_user.id))
                except Exception:
                    pass  # Best-effort; don't block logout
    except Exception:
        pass  # Best-effort; don't block logout

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
