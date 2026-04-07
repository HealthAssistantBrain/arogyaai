from fastapi import APIRouter
from app.schema import IngestRequest, ResponseEnvelope
from app.service import process_wearable_data

router = APIRouter()

@router.post("/ingest", response_model=ResponseEnvelope)
async def ingest_data(payload: IngestRequest):
    try:
        if process_wearable_data is None:
            raise Exception("Service not implemented")

        result = await process_wearable_data(payload)

        return {
            "success": True,
            "status": "ready",
            "data": result,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "status": "fallback",
            "data": None,
            "error": str(e)
        }
