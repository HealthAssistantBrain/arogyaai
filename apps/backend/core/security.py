import uuid
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt

from core.config import settings

# Passlib context utilizing bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the BCrypt hash stored in the DB."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Returns a BCrypt hash of the given password string."""
    return pwd_context.hash(password)

def create_access_token(subject: str | uuid.UUID, expires_delta: timedelta | None = None) -> str:
    """Generates a short-lived JSON Web Token for stateless access."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: str | uuid.UUID) -> tuple[str, datetime]:
    """Generates a long-lived JWT token specifically for DB revocation mapping."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    refresh_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return refresh_token, expire
