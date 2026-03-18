import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ArogyaAI"
    
    # SECURITY DEFAULT (Must be overridden in production)
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkey_change_in_production")
    ALGORITHM: str = "HS256"
    
    # TOKENS
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    class Config:
        case_sensitive = True

settings = Settings()
