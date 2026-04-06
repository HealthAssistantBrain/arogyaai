from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="Wearable Data Pipeline",
    description="Independent microservice for ingesting and processing IoT/wearable telemetry.",
    version="1.0.0"
)

app.include_router(router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "wearable-service"}
