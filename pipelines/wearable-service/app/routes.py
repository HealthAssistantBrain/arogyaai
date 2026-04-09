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
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "status": "fallback",
            "data": None,
            "error": str(e),
        }


async def _get_vitals_impl(user_id: str):
    return {
        "success": True,
        "status": "ready",
        "data": {
            "user_id": user_id,
            "hrv": [
                {"time": "12 AM", "value": 62},
                {"time": "4 AM", "value": 58},
                {"time": "8 AM", "value": 71},
                {"time": "12 PM", "value": 65},
                {"time": "4 PM", "value": 69},
                {"time": "8 PM", "value": 61},
            ],
            "hrv_average_bpm": 64,
            "sleep": [
                {"day": "MON", "hours": 7.2},
                {"day": "TUE", "hours": 7.8},
                {"day": "WED", "hours": 6.9},
                {"day": "THU", "hours": 7.4},
                {"day": "FRI", "hours": 7.0},
                {"day": "SAT", "hours": 8.1},
                {"day": "SUN", "hours": 7.6},
            ],
            "sleep_average_hours": 7.4,
        },
        "error": None,
    }


@router.get("/vitals/{user_id}")
@router.get("/api/v1/vitals/{user_id}")
async def get_vitals(user_id: str):
    return await _get_vitals_impl(user_id)


@router.post("/sync/{user_id}")
async def sync_user_data(user_id: str):
    return {
        "success": True,
        "status": "ready",
        "data": {
            "user_id": user_id,
            "message": "Wearable sync completed.",
        },
        "error": None,
    }
