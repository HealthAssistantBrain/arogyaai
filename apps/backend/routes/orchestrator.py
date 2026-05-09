from fastapi import APIRouter

from services.orchestrator import get_orchestrator


router = APIRouter(tags=["AI Orchestrator"])


@router.get("/health/orchestrator")
@router.get("/api/v1/health/orchestrator")
async def orchestrator_health():
    return await get_orchestrator().health_snapshot()
