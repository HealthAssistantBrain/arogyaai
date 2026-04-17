# ArogyaAI Platform

ArogyaAI is a production-grade predictive health intelligence platform designed to ingest continuous patient data, parse complex medical reports, and deliver actionable ML-powered predictive insights.

---

## Architecture Overview

The system follows a strict microservices architecture configured for high reliability and scale:

1. **Backend Orchestrator**: FastAPI application coordinating ingestion, auth, and routing logic.
2. **Prediction Service**: Dedicated Python microservice running complex clinical rule engines and ML model inference.
3. **RAG Service**: Dedicated service integrating semantic search to produce clinically-grounded explanations.
4. **Celery Workers**: Background event processors to compute heavy ML features and baselines.

### Infrastructure stack

* **Database**: PostgreSQL + TimescaleDB (for high-throughput timeseries telemetry).
* **Caching & Queues**: Redis.
* **Vector Search**: Qdrant (for RAG document retrieval).
* **Frontend**: React/TypeScript application utilizing Zustand caching mechanisms.

---

## Core Capabilities

* **Continuous Ingestion**: Collects and normalizes Google Fit and manual vitals data.
* **Report Parsing**: Maps uploaded medical records into discrete `LabValue` metrics.
* **Risk Prediction**: Asynchronous Celery pipeline that rolls up a user's health context (`FeatureSnapshot`), scores it, and dictates a risk trajectory.
* **SHAP Explainability**: Demystifies ML outputs by showing patients the exact metric drivers augmenting their risk.
* **RAG Clinical Context**: Uses Qdrant vector-search to explain complex health queries based on approved medical corpora.

---

## Tech Stack

* **Language**: Python 3.10+ / TypeScript
* **Framework**: FastAPI (Backend) / React (Frontend)
* **ORM / DB**: SQLAlchemy / Alembic / Postgres (TimescaleDB)
* **Async Workers**: Celery
* **ML**: Custom Rule Engines, SHAP integration

---

## Setup Instructions

Ensure Docker and Docker Compose are installed.

```bash
# 1. Environment setup
cp .env.template .env
# ensure ports 8000, 8001, 8002, 6333, 6379, 5432, 5173, 5050 are open

# 2. Boot the entire infrastructure
docker-compose up --build -d

# 3. Apply database migrations
docker-compose exec backend pip install -r requirements.txt
docker-compose exec backend alembic upgrade head
```

---

## API Structure

Core routing groups mapped in the backend:

* `/api/v1/auth/*`: JWT login, registration, and session token renewal.
* `/api/v1/users/*`: Profile details and onboarding operations.
* `/api/v1/vitals/*` & `/api/v1/wearable/*`: Timeseries telemetry ingestion endpoints.
* `/api/v1/reports/*`: File upload and processing APIs.
* `/api/v1/intelligence/*`: Triggers ML risk estimations (`/predict`) and RAG textual simplifications (`/explain`).
* `/api/v1/alerts/*`: System and anomoly notification polling.
* `/health`: Readiness and liveness checks for all subservices.

## Data Flow & Scaling

1. **Synchronous Flow**: Rapid inserts to Database and simple JWT validation are executed synchronously to ensure a responsive frontend.
2. **Asynchronous Flow**: Feature compilation, ML inference, and SHAP evaluation are pushed to the `celery-worker` using chained tasks (`feature` -> `ml` -> `shap` -> `ingestion`).
3. **Resilience**: The backend defaults to local rule thresholds (`is_fallback=True`) if the external ML node is unresponsive, guaranteeing a response to the user.
