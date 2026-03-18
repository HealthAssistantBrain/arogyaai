from fastapi import FastAPI

app = FastAPI(title="ArogyaAI Auth Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auth-service"}
