from app.schema import IngestRequest

async def process_wearable_data(request: IngestRequest) -> dict:
    """
    Core business logic for the pipeline.
    Independent from ArogyaAI core database; do NOT import ArogyaAI database sessions.
    """
    # Pipeline specific ML/ETL logic goes here
    
    simulated_vitals = {
        "heart_rate_avg": 72,
        "hrv": 45,
        "sleep_score": 88
    }
    
    return simulated_vitals
