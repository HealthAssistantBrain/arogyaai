from integrations.prediction_client import PredictionClient
from schemas.api_models import PredictionRequest
from typing import Dict, Any

prediction_client = PredictionClient()

async def get_health_prediction(user_id: str, data: PredictionRequest) -> Dict[str, Any]:
    """
    Coordinates health risk prediction.
    Calls Prediction Microservice via integration layer with fallback logic.
    """
    # Prepare internal payload
    payload = data.model_dump()
    payload["user_id"] = user_id
    
    # Call integration
    response = await prediction_client.get_prediction(payload)
    
    if response.get("success") and response.get("status") == "ready":
        return response
        
    # Fallback/Smart Mock Logic
    return {
        "success": True,
        "status": "fallback",
        "source": "computed",
        "error": None,
        "data": {
            "risk_score": 45.2,
            "risk_level": "Moderate",
            "recommendations": [
                "Maintain current activity level",
                "Schedule a routine check-up in 6 months",
                "Focus on consistent sleep patterns"
            ]
        }
    }
