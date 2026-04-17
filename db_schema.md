# Database Architecture (ArogyaAI)

## 1. Overview

ArogyaAI runs on a **PostgreSQL** database, utilizing **TimescaleDB** for high-performance time-series data related to user health metrics.

## 2. Table Definitions

### User Management & Auth

* **`users`**: Core user accounts (email, password_hash).
* **`user_profile`**: Personal details (name, avatar, phone).
* **`sessions`**: Refresh tokens and session control.
* **`user_settings`**: Global user preferences.
* **`logs`**: Audit logging for user/system actions.

### Health Data & Records

* **`health_profiles`**: Demographics and biometrics (DOB, height, weight, blood group, allergies).
* **`medical_history`**: Past conditions and treatments.
* **`reports`**: Uploaded medical documents (PDF/images) and their processing status.
* **`lab_results`** & **`lab_values`**: Extracted biomarker values from parsed reports.

### Devices & Ingestion

* **`devices`** & **`user_devices`**: Registered trackers (Apple Health, Fitbit, Google Fit).
* **`google_fit_connections`**: Specific OAuth tokens and sync status for Google Fit.

### Time-Series Metrics (TimescaleDB)

* **`vitals_data`**: Vital signs (HR, BP, SpO2, Temperature). Time column: `recorded_at`.
* **`wearable_data`**: Aggregated daily/hourly metrics (steps, calories, sleep). Time column: `recorded_at`.
* **`user_vitals`**: Discrete generic readings. Time column: `timestamp`.
* **`lab_results`**: Historical lab trends. Time column: `timestamp`.

*(Note: These tables are architected to be Hypertables in TimescaleDB for partition-based chunking on the respective time columns, and are denoted as "TimescaleDB-ready" in models)*

### Predictions & Intelligence

* **`risk_scores`**: Calculated ML predictions with confidence scores and model versions.
* **`recommendations`**: AI-generated action items tied to specific risk scores.
* **`shap_values`**: Explained ML feature impact per prediction (Direction, SHAP value).
* **`health_scores`**: Computed overall holistic health scores (Risk, Lifestyle, Vitals components).
* **`feature_snapshots`** & **`baseline_metrics`**: Pre-computed features tracking the ML inputs over time.

### Engagement

* **`alerts`** & **`notifications`**: System alerts (anomalies, missing syncs) to prompt user action.

## 3. Key Relationships

* **User -> Reports / Lab Values**: A `User` (1) has many `Report`s (N). Each `Report` has many `LabValue`s.
* **User -> Vitals / Wearables**: Continuous insertion into `vitals_data` and `wearable_data` assigned via `user_id`.
* **Report -> Risk Score**: Generating an ML prediction (`RiskScore`) is 1:1 tied to a `Report` analysis when applicable, or generated standalone based on time-series history.
* **Risk Score -> SHAP / Recommendations**: A `RiskScore` spawns multiple `ShapValueRecord`s explaining the score, and multiple `Recommendation`s.
