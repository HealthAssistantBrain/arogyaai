from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field
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

class PasswordUpdate(BaseModel):
    password: str
    confirm_password: str


class OAuthLoginRequest(BaseModel):
    provider: Optional[str] = None
    access_token: str

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
    days: int = 7


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    occupation: Optional[str] = None
    city: Optional[str] = None
    marital_status: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    family_history: Optional[str] = None
    surgeries: Optional[str] = None
    hospitalizations: Optional[bool] = None
    hospitalization_details: Optional[str] = None
    current_medications: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = None
    smoking: Optional[bool] = None
    alcohol: Optional[bool] = None
    appetite: Optional[str] = None
    bowel_habits: Optional[str] = None

class ProfileUpdateSchema(BaseModel):
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None


class UserOnboardingSave(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    city: Optional[str] = None
    marital_status: Optional[str] = None
    phone_number: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[int] = None
    goals: Optional[str] = None
    family_history: Optional[str] = None
    surgeries: Optional[str] = None
    hospitalizations: Optional[bool] = None
    hospitalization_details: Optional[str] = None
    current_medications: Optional[str] = None
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = None
    smoking: Optional[bool] = None
    alcohol: Optional[bool] = None
    appetite: Optional[str] = None
    bowel_habits: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    is_onboarding_done: Optional[bool] = None
    onboarding_step: Optional[int] = None


class UserSettingsUpdate(BaseModel):
    auto_fetch_enabled: bool
    fetch_interval_minutes: int


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    ai_insights_email: Optional[bool] = None
    ai_insights_push: Optional[bool] = None
    health_alerts_email: Optional[bool] = None
    health_alerts_push: Optional[bool] = None
    reminders_email: Optional[bool] = None
    reminders_push: Optional[bool] = None


class PushSubscriptionPayload(BaseModel):
    endpoint: str
    expirationTime: Optional[int] = None
    keys: dict[str, str]


class NotificationDeviceRegistration(BaseModel):
    subscription: PushSubscriptionPayload
    platform: str = "web"
    device_name: Optional[str] = None


class SimulatorInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sleep: Optional[float] = Field(default=None, validation_alias=AliasChoices("sleep", "sleep_hours"))
    steps: Optional[int] = Field(default=None, validation_alias=AliasChoices("steps", "daily_steps"))
    heart_rate: Optional[int] = Field(default=None, validation_alias=AliasChoices("heart_rate", "heart_rate_bpm"))
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    weight: Optional[float] = Field(default=None, validation_alias=AliasChoices("weight", "weight_kg"))
    bmi: Optional[float] = None
    glucose: Optional[float] = None
    hba1c: Optional[float] = Field(default=None, validation_alias=AliasChoices("hba1c", "a1c"))
    diet_score: Optional[float] = None
    spo2: Optional[float] = Field(default=None, validation_alias=AliasChoices("spo2", "oxygen_saturation"))
    resp_rate: Optional[int] = Field(default=None, validation_alias=AliasChoices("resp_rate", "respiratory_rate"))
    activity: Optional[float] = None
    air_quality: Optional[float] = Field(default=None, validation_alias=AliasChoices("air_quality", "aqi"))
    smoking: Optional[bool] = None


class DiseaseSimulationRequest(BaseModel):
    focus_condition: str = "cardiovascular"
    timeframe_months: int = 6
    simulation: SimulatorInput = Field(default_factory=SimulatorInput)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
