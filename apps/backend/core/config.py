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
