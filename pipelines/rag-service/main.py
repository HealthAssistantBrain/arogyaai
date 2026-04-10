from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="ArogyaAI Rag Service")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "rag-service"}


class ExplainRequest(BaseModel):
    prediction_id: str = Field(..., min_length=1)


@app.post("/explain")
async def explain_prediction(payload: ExplainRequest):
    return {
        "success": True,
        "status": "ready",
        "error": None,
        "data": {
            "factors": [
                {"name": "blood_pressure", "impact": "+15%"},
                {"name": "activity_level", "impact": "+8%"},
            ],
            "summary": f"Explanation generated for prediction {payload.prediction_id}. The primary drivers are elevated systolic pressure and family history.",
        },
    }
 
