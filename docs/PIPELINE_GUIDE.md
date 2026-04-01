# ArogyaAI Strict Pipeline Integration Guide

To ensure high reliability and to prevent localized failures from crashing the entire application, ArogyaAI utilizes a **Strict Pipeline Integration Architecture**.

All Machine Learning models, RAG document engines, and IoT ingestion pipelines must be built as autonomous, containerized microservices that follow these unbreakable rules:

## 1. Directory Structure

Pipelines live in the `services/` root directory. Each pipeline follows a mandatory template:

```
services/service-name/
├── app/
│   ├── main.py         (FastAPI entrypoint)
│   ├── routes.py       (API Controllers)
│   ├── schema.py       (Pydantic input/output contracts)
│   ├── service.py      (Core logic / ML inference)
│   └── utils.py        (Logging, etc.)
├── requirements.txt    (Isolated dependencies)
├── Dockerfile          (Deployment instructions)
└── README.md           (Service description)
```

*(An example of this layout can be found in `services/wearable-service/`)*

## 2. API Contract (The Envelope)

ArogyaAI's frontend and core backend strictly require a guaranteed JSON envelope wrapper. **NO EXCEPTIONS.**
Even if an internal failure occurs, your service HTTP responses MUST comply with this envelope structure (or the backend integration client will catch the 500 and synthesize a generic fallback anyway).

### Structure

```json
{
  "success": true,
  "status": "ready",     // Must be: "ready", "processing", or "fallback"
  "data": { ... },       // Your actual payload output goes here
  "error": null          // String message on failure; null on success
}
```

### Health Check Rule

Every pipeline **MUST** expose a `GET /health` endpoint that returns `{"status": "ok"}` or the standardized envelope above. This allows the backend orchestration layer to determine if your service is alive before sending data.

### Example Domain Endpoint (`POST /predict`)

```json
// Request
{
  "user_id": "1234",
  "payload": { "glucose_level": 110 }
}

// Response
{
  "success": true,
  "status": "ready",
  "data": { "risk_score": 12 },
  "error": null
}
```

## 3. Backend Integration Restrictions

Pipelines **NEVER** talk directly to the UI, nor do they access the ArogyaAI PostgreSQL database.

All pipeline integrations happen strictly through the `backend/integrations/` layer.

### Example Integration Architecture

When adding a new pipeline, you must write an integration client wrapper inside the core `backend`:

**File**: `apps/backend/integrations/my_new_service_client.py`

```python
from integrations.base_client import BaseAPIClient

class MyNewServiceClient(BaseAPIClient):
    def __init__(self):
        # Maps to the docker-compose service name and internal port
        super().__init__(base_url="http://my-new-service:8004")

    async def compute_something(self, user_id: str, data: dict):
        response = await self.post("/compute", json={"user_id": user_id, "payload": data})
        return response # The base_client ensures the Response Envelope format is returned safely
```

## 4. Fallback Requirement

If your pipeline's internal dependencies fail (e.g., an external ML API goes down), your service logic MUST manually trap the error and return a safe default fallback.

For instance:

```json
{
  "success": false,
  "status": "fallback",
  "data": null,
  "error": "ML Inference timed out"
}
```

## 5. Summary of Developer Rules

- ❌ **No Direct DB Access**: Do not query the primary Postgres DB. Use the Integration API endpoints if you need user data.
- ❌ **No Frontend Dependencies**: Your pipeline outputs raw data. Wait for the `dashboard_service.py` to format it for the frontend widgets.
- ❌ **No Shared State**: Microservices must not share Redis or memory caches with the primary backend unless explicitly architected as a decoupled Pub/Sub queue.
- ✔️ **Dockerized Check**: Must expose an internal port, run independently, and be registered in `docker-compose.yml`.
