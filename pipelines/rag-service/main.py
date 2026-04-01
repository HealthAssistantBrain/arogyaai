from fastapi import FastAPI

app = FastAPI(title="ArogyaAI Rag Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rag-service"}
