# ArogyaAI Pipeline Development Entry

## Where to build?

Go to:

/pipelines/

Each folder = one independent microservice.

---

## Available Pipelines

- prediction-service → ML risk prediction
- rag-service → medical explanation system
- wearable-service → IoT / wearable ingestion

---

## What to do?

1. Choose your pipeline
2. Go inside its folder
3. Follow structure defined in:

docs/PIPELINE_GUIDE.md

---

## How it connects?

Your pipeline → backend/integrations → backend/services → frontend

---

## Rules (STRICT)

- Do NOT modify frontend
- Do NOT modify backend routes
- Do NOT access PostgreSQL directly
- Do NOT bypass integration layer

---

## API Requirement

All responses MUST follow:

{
  "success": true,
  "status": "ready | processing | fallback",
  "data": {...},
  "error": null
}

---

## Running locally

Start everything:

docker-compose up --build

---

## Health Check

Each pipeline must expose:

GET /health → { "status": "ok" }

---

## If your service fails

Backend will automatically fallback.

No frontend changes needed.

# ArogyaAI Pipeline Development Entry

## Where to build?

Go to:

/pipelines/

Each folder = one independent microservice.

---

## Available Pipelines

- prediction-service → ML risk prediction
- rag-service → medical explanation system
- wearable-service → IoT / wearable ingestion

---

## What to do?

1. Choose your pipeline
2. Go inside its folder
3. Follow structure defined in:

docs/PIPELINE_GUIDE.md

---

## How it connects?

Your pipeline → backend/integrations → backend/services → frontend

---

## Rules (STRICT)

- Do NOT modify frontend
- Do NOT modify backend routes
- Do NOT access PostgreSQL directly
- Do NOT bypass integration layer

---

## API Requirement

All responses MUST follow:

{
  "success": true,
  "status": "ready | processing | fallback",
  "data": {...},
  "error": null
}

---

## Test locally

docker-compose up --build

---

## Health Check

Each pipeline must expose:

GET /health → { "status": "ok" }

---

## If your service fails

Backend will automatically fallback.

No frontend changes needed.
