from pydantic import BaseModel, EmailStr, Field
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
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None


class UserOnboardingSave(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    is_onboarding_done: Optional[bool] = None
    onboarding_step: Optional[int] = None


class UserSettingsUpdate(BaseModel):
    auto_fetch_enabled: bool
    fetch_interval_minutes: int


class SimulatorInput(BaseModel):
    sleep_hours: Optional[float] = None
    daily_steps: Optional[int] = None
    weight_kg: Optional[float] = None
    stress_level: Optional[int] = None
    weekly_exercise_hours: Optional[float] = None
    heart_rate_bpm: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    spo2: Optional[float] = None
    fasting_glucose: Optional[float] = None


class DiseaseSimulationRequest(BaseModel):
    focus_condition: str = "cardiovascular"
    timeframe_months: int = 6
    simulation: SimulatorInput = Field(default_factory=SimulatorInput)
