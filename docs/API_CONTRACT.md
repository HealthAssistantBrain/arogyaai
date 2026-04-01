# ArogyaAI API Contract v1.0

This document defines the standardized communication protocols between the ArogyaAI frontend and backend.

## 1. Global Response Envelope

All API responses MUST follow this JSON structure:

```json
{
  "success": boolean,
  "status": "ready" | "processing" | "fallback",
  "data": object | array | null,
  "error": string | null
}
```

### Field Definitions

- **success**: Indicates if the request was handled without an unhandled exception.
- **status**:
  - `ready`: Data is real, fresh, and sourced from primary pipelines.
  - `processing`: Request is accepted, but data is being computed (show shimmer/loading).
  - `fallback`: Pipeline is unavailable; returning cached or smart-mock data.
- **data**: The requested payload.
- **error**: Human-readable error message (only if `success` is false).

## 2. Status Code Standards

- `200 OK`: Successful request.
- `201 Created`: Resource successfully created (e.g., Signup).
- `400 Bad Request`: Validation error or malformed body.
- `401 Unauthorized`: Missing or invalid JWT.
- `403 Forbidden`: Insufficient permissions (Role-based).
- `404 Not Found`: Resource does not exist.
- `500 Internal Server Error`: Unhandled backend exception.
- `503 Service Unavailable`: Critical infrastructure failure (DB or Redis down).

## 3. Module Schemas

### Auth

- `POST /api/v1/auth/login` -> Returns `{ token, user }`
- `POST /api/v1/auth/signup` -> Returns `{ token, user }`

### Dashboard

- `GET /api/v1/health/score` -> Returns health score analytics.
- `GET /api/v1/health/history` -> Returns time-series health data.

### Intelligence

- `POST /api/v1/intelligence/predict` -> Triggers ML prediction via Integration layer.
- `POST /api/v1/intelligence/explain` -> Triggers RAG explanation via Integration layer.
