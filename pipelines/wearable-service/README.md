# ArogyaAI Wearable Data Service

This is an independent microservice responsible for ingesting, validating, and normalizing wearable device telemetry (e.g., Apple Watch, Oura, Fitbit).

## Pipeline Contract Rules

1. **No Backend Database Access**: Do NOT import or connect to the PostgreSQL database from this pipeline.
2. **Strict Response Envelope**: All API responses MUST return exactly: `{"success": true/false, "status": "ready"|"processing"|"fallback", "data": {}, "error": str}`
3. **Containerized**: Must run via its `Dockerfile` and be mounted in the root `docker-compose.yml`.

## Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```
