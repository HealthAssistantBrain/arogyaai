from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="Wearable Data Pipeline",
    description="Independent microservice for ingesting and processing IoT/wearable telemetry.",
    version="1.0.0"
)

app.include_router(router)

@app.get("/health", tags=["System"])
def health_check():
    """
    Mandatory pipeline health check.
    MUST return {"status": "ok"} or standard ArogyaAI envelope.
    """
    return {"status": "ok"}
