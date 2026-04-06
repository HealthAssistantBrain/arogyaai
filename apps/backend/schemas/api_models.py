from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    dob: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class HealthDataUpload(BaseModel):
    user_id: str
    heart_rate: Optional[int]
    blood_pressure: Optional[str]

class PredictionRequest(BaseModel):
    user_id: str
    data_points: dict

class PredictionResponse(BaseModel):
    risk_score: float
    risk_level: str
    recommendations: list[str]

class ExplanationRequest(BaseModel):
    prediction_id: str

class ExplanationResponse(BaseModel):
    factors: list[dict]
    summary: str


class GoogleFitConnectRequest(BaseModel):
    timezone: Optional[str] = None
    redirect_path: Optional[str] = "/device-settings/google-fit"


class GoogleFitSyncRequest(BaseModel):
    timezone: Optional[str] = None
    days: int = 30


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
