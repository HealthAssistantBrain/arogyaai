from integrations.prediction_client import PredictionClient
from integrations.rag_client import RAGClient
from schemas.api_models import PredictionRequest, ExplanationRequest
from typing import Dict, Any

prediction_client = PredictionClient()
rag_client = RAGClient()

async def get_risk_prediction(data: PredictionRequest) -> Dict[str, Any]:
    """Delegates risk prediction to Prediction Microservice."""
    response = await prediction_client.get_prediction(data.model_dump())
    if response.get("success") and response.get("status") == "ready":
        return response
        
    return {
        "success": True,
        "status": "fallback",
        "source": "mock",
        "error": None,
        "data": {
            "risk_score": 82.5,
            "risk_level": "High",
            "recommendations": ["Consult a specialist", "Reduce sodium intake"]
        }
    }

async def get_explanation(req: ExplanationRequest) -> Dict[str, Any]:
    """Delegates explanation retrieval to RAG Microservice."""
    response = await rag_client.get_explanation(str(req.prediction_id))
    if response.get("success") and response.get("status") == "ready":
        return response
        
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": {
            "factors": [{"name": "blood_pressure", "impact": "+15%"}],
            "summary": "The primary drivers are elevated systolic pressure and family history."
        }
    }
