from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class IngestRequest(BaseModel):
    user_id: str
    device_type: str = Field(..., description="E.g., apple_watch, fitbit, oura")
    payload: Dict[str, Any]

class ResponseEnvelope(BaseModel):
    success: bool
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
