from fastapi import APIRouter
from app.schema import IngestRequest, ResponseEnvelope
from app.service import process_wearable_data

router = APIRouter()

@router.post("/ingest", response_model=ResponseEnvelope)
async def ingest_data(payload: IngestRequest):
    """
    Standardized pipeline ingestion endpoint.
    Guarantees the strict {success, status, data, error} envelope.
    """
    try:
        result = await process_wearable_data(payload)
        return {"success": True, "status": "ready", "data": result, "error": None}
    except Exception as e:
        # Crucial fallback compliance for ArogyaAI pipelines
        return {"success": False, "status": "fallback", "data": None, "error": str(e)}
