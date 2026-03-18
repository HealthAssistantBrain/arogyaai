from fastapi import FastAPI

app = FastAPI(title="ArogyaAI Prediction Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "prediction-service"}
