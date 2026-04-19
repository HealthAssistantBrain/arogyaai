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
    REPORT_UPLOAD_DIR: str = os.getenv("REPORT_UPLOAD_DIR", str(Path("uploads") / "reports"))

    # GOOGLE FIT
    GOOGLE_FIT_CLIENT_ID: str = os.getenv("GOOGLE_FIT_CLIENT_ID", "")
    GOOGLE_FIT_CLIENT_SECRET: str = os.getenv("GOOGLE_FIT_CLIENT_SECRET", "")
    GOOGLE_FIT_REDIRECT_URI: str = os.getenv("GOOGLE_FIT_REDIRECT_URI", "")
    GOOGLE_FIT_DEFAULT_TIMEZONE: str = os.getenv("GOOGLE_FIT_DEFAULT_TIMEZONE", "Asia/Kolkata")
    APP_ENCRYPTION_KEY: str = os.getenv("APP_ENCRYPTION_KEY", "")

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
