from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

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
