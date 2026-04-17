# Pipeline Architecture (ArogyaAI)

## 1. Overview

The ArogyaAI system leverages a deeply decoupled asynchronous architecture. CPU-intensive or long-running tasks—such as external data fetching, ML interference, and report parsing—are managed by dedicated pipelines running on **Celery**, communicating via **Redis** workers.

## 2. Ingestion Pipeline

**Trigger**: Chron-based (Google Fit Worker) or direct API calls (`/vitals`, `/wearable`).
**Processing steps**:

1. External service tokens are refreshed.
2. Data points are fetched and normalized to standard ArogyaAI schema.
3. Payload is stored in TimescaleDB hypertables (`wearable_data`, `vitals_data`).
**Async Worker**: `compute_baseline` (Queue: `ingestion`) recalculates rolling averages (`baseline_metrics`).

## 3. OCR Pipeline

**Trigger**: User uploads a report (`/reports/upload`).
**Processing steps**:

1. File is persisted to storage.
2. Extract text/values using `ReportService.upload_and_summarize` logic.
3. Detected biomarkers map to `lab_values`.
**Output**: `Report` is marked `COMPLETED`.

## 4. ML Prediction Pipeline

**Trigger**: Explicit analysis requests (`/api/v1/intelligence/predict`) or chained pipeline completion.
**Flow (Celery Chain)**:

1. `compute_features` (Queue: `feature`): Rolls up historical time-series plus current lab values into a `FeatureSnapshotRecord`.
2. `run_inference` (Queue: `ml`): Passes the flat feature vector to `prediction-service`. Generates a `RiskScore` (Low/Moderate/High) and `Recommendations`.
**Output**: `RiskScore` is saved to DB, UI is notified optionally via WebSockets.

## 5. SHAP Explainability Pipeline

**Trigger**: Immediately follows `run_inference` in the Celery chain.
**Processing steps**:

1. Worker executes `compute_shap` (Queue: `shap`).
2. Requests the prediction interpretation from `prediction-service`.
3. Stores `ShapValueRecord` corresponding to the exact `prediction_id` identifying factors (e.g. +15% impact from Blood Pressure).

## 6. RAG Pipeline

**Trigger**: User clicks "Explain this to me" on a report/prediction (`/api/v1/intelligence/explain`).
**Processing steps**:

1. Call to `rag-service` (port `8002`).
2. Service vector-searches **Qdrant** for clinical guidelines matching the patient's anomalous factors.
3. LLM synthesizes an overarching, patient-friendly summary.
**Output**: JSON returning `factors` and `summary` text directly to the frontend.

## 7. Failure Handling

* Celery workers rely on configured retries for transient backend exceptions.
* Fallback risk scores (Rule-Engine) are generated locally if the prediction microservice is unavailable (`prediction_source = 'rule_fallback'`).
