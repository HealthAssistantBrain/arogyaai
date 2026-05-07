import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ArogyaAI"
    
    # SECURITY DEFAULT (Must be overridden in production)
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkey_change_in_production")
    ALGORITHM: str = "HS256"
    
    # TOKENS
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # APP URLS
    APP_ENV: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production")).strip().lower()
    FRONTEND_APP_URL: str = os.getenv("FRONTEND_APP_URL", "http://localhost:5173")
    BACKEND_PUBLIC_URL: str = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    REPORT_UPLOAD_DIR: str = os.getenv("REPORT_UPLOAD_DIR", str(Path("uploads") / "reports"))  # DEPRECATED — use Supabase Storage

    # SUPABASE STORAGE
    SUPABASE_BUCKET_NAME: str = os.getenv("SUPABASE_BUCKET_NAME", "medical-reports")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # GOOGLE FIT
    GOOGLE_FIT_CLIENT_ID: str = os.getenv("GOOGLE_FIT_CLIENT_ID", "")
    GOOGLE_FIT_CLIENT_SECRET: str = os.getenv("GOOGLE_FIT_CLIENT_SECRET", "")
    GOOGLE_FIT_REDIRECT_URI: str = os.getenv("GOOGLE_FIT_REDIRECT_URI", "")
    GOOGLE_FIT_DEFAULT_TIMEZONE: str = os.getenv("GOOGLE_FIT_DEFAULT_TIMEZONE", "Asia/Kolkata")
    GOOGLE_FIT_CA_BUNDLE: str = os.getenv("GOOGLE_FIT_CA_BUNDLE", "")
    GOOGLE_FIT_SSL_VERIFY: bool = os.getenv("GOOGLE_FIT_SSL_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"}
    APP_ENCRYPTION_KEY: str = os.getenv("APP_ENCRYPTION_KEY", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:notifications@arogyaai.local")

    # SUPABASE OAUTH
    SUPABASE_URL: str = (
        os.getenv("SUPABASE_URL", "")
        .strip()
        .removeprefix("SUPABASE_URL=")
        .removeprefix("supabase_url=")
    )
    SUPABASE_ANON_KEY: str = (
        os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
        .strip()
        .removeprefix("VITE_SUPABASE_ANON_KEY=")
        .removeprefix("SUPABASE_ANON_KEY=")
        .removeprefix("vite_supabase_anon_key=")
        .removeprefix("supabase_anon_key=")
    )
    SUPABASE_AUDIENCE: str = os.getenv("SUPABASE_AUDIENCE", "authenticated")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Placeholder patterns that indicate a value hasn't been configured
_PLACEHOLDER_PATTERNS = [
    "your_jwt_secret_key_here",
    "your_encryption_key_here",
    "your-project-id.supabase.co",
    "your_supabase_anon_key_here",
    "your_supabase_service_role_key_here",
    "supersecretkey_change_in_production",
]


def _is_placeholder(value: str) -> bool:
    """Check if a value is still a placeholder."""
    if not value:
        return True
    return any(pattern in value for pattern in _PLACEHOLDER_PATTERNS)


def _validate_settings():
    """Validate critical environment variables at startup.
    
    Provides clear, actionable error messages telling the developer
    exactly what to fix and how to generate the missing values.
    """
    missing = []
    
    if _is_placeholder(settings.SECRET_KEY):
        missing.append(
            'JWT_SECRET_KEY — Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    if _is_placeholder(settings.APP_ENCRYPTION_KEY):
        missing.append(
            'APP_ENCRYPTION_KEY — Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    if _is_placeholder(settings.SUPABASE_URL):
        missing.append(
            "SUPABASE_URL — Get from: Supabase Dashboard → Project Settings → API"
        )
    if _is_placeholder(settings.SUPABASE_ANON_KEY):
        missing.append(
            "SUPABASE_ANON_KEY — Get from: Supabase Dashboard → Project Settings → API → anon key"
        )
    if _is_placeholder(settings.SUPABASE_SERVICE_ROLE_KEY):
        missing.append(
            "SUPABASE_SERVICE_ROLE_KEY — Get from: Supabase Dashboard → Project Settings → API → service_role key"
        )
    if not os.getenv("DATABASE_URL") and not os.getenv("POSTGRES_DB"):
        missing.append(
            "DATABASE_URL or POSTGRES_DB — Set your PostgreSQL connection string"
        )
        
    if missing:
        border = "=" * 70
        items = "\n".join(f"  ✗ {m}" for m in missing)
        raise RuntimeError(
            f"\n{border}\n"
            f"  AROGYAAI STARTUP FAILURE — Missing Environment Variables\n"
            f"{border}\n\n"
            f"The following variables are missing or using placeholder values:\n\n"
            f"{items}\n\n"
            f"Setup instructions:\n"
            f"  1. cp .env.template .env\n"
            f"  2. Fill in the values listed above\n"
            f"  3. Restart the application\n\n"
            f"See README.md for full setup guide.\n"
            f"{border}\n"
        )

_validate_settings()
