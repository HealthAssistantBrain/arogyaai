from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import modular routers
from routes import auth, intelligence, users

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ArogyaAI Main Backend",
    description="Orchestrator API routing to specialized Microservices.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
def health_check():
    """Basic health check confirming the Orchestrator is alive."""
    return {"status": "ok", "service": "backend", "message": "ArogyaAI Backend Active"}

# Mount modular routers
app.include_router(auth.router)       # /auth/*
app.include_router(users.router)      # /users/*  (includes /users/me)
app.include_router(intelligence.router)
