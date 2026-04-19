# ArogyaAI 🧠⚕️

ArogyaAI is a production-grade predictive health intelligence platform. It is designed to ingest continuous patient data from wearables, parse complex medical reports using AI, and deliver actionable ML-powered predictive insights.

---

## 1. Overview

ArogyaAI helps users take control of their health through data-driven insights.

**Key Features:**

- **Automated Report Parsing:** Upload PDF or image-based medical reports; our system extracts biomarkers using OCR.
- **AI-Powered Risk Prediction:** Advanced ML models predict health risks and trajectory based on your data.
- **Holistic Health Tracking:** Integrate Google Fit data (steps, sleep, heart rate) alongside lab results.
- **Smart Recommendations:** Receive personalized, clinically-grounded health advice.
- **Secure Storage:** All medical reports are stored safely in Supabase Cloud Storage.

---

## 2. Tech Stack

The platform is built using a modern, scalable microservices architecture:

- **Frontend:** React / TypeScript with Zustand for state management and Framer Motion for smooth UI.
- **Backend:** FastAPI (Python 3.11) acting as the central orchestrator.
- **Asynchronous Processing:** Celery + Redis for heavy ML feature computation and pipeline execution.
- **Database:** PostgreSQL + TimescaleDB (for high-throughput time-series telemetry).
- **Vector Search:** Qdrant (for Reranking and RAG clinical explanations).
- **Cloud Storage:** Supabase Storage for secure medical document management.
- **AI/ML:** Combined OCR mapping, custom Rule Engines, and SHAP explainability.

---

## 3. Architecture (Simple Explanation)

The system works in a streamlined pipeline to ensure data integrity and real-time response:

1. **Upload:** User uploads a report via the React UI.
2. **Backend:** FastAPI receives the file and securely stores it in Supabase.
3. **Celery:** A background task is triggered to process the report.
4. **AI Engine:** The "Prediction Service" performs OCR and evaluates health markers.
5. **DB:** Extracted metrics and risk scores are saved to PostgreSQL.
6. **UI:** The dashboard updates automatically to show you the new analysis and trends.

---

## 4. Project Structure

```bash
├── apps/
│   ├── backend/          # FastAPI Orchestrator, Core Logic & API
│   └── frontend/         # React Web Application
├── pipelines/
│   ├── prediction-service/ # ML Inference and Clinical Rule Engine
│   ├── rag-service/        # RAG-based Medical Explanation System
│   └── wearable-service/   # IoT Ingestion & Normalization
├── infra/                # Nginx and Infrastructure configurations
└── docker-compose.yml    # Service orchestration
```

---

## 5. Prerequisites

To run ArogyaAI locally, ensure you have the following installed:

- **Git:** [Download](https://git-scm.com/downloads)
- **Docker & Docker Compose:** [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Node.js (v18+):** [Download](https://nodejs.org/)
- **Python (v3.11):** (Included in Docker containers)

---

## 6. Environment Setup

### Root Folder `.env`

Copy the template to create your environment file:

```bash
cp .env.template .env
```

Fill in the following critical variables:

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | Connection string for Postgres (default provided in template). |
| `REDIS_URL` | URL for the Redis messenger (default provided). |
| `SUPABASE_URL` | Your Supabase Project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Your **Service Role** key (Required for backend uploads). |
| `SUPABASE_BUCKET_NAME` | The name of your storage bucket (e.g., `reports`). |
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL`. |
| `VITE_SUPABASE_ANON_KEY` | Your project's **Anon/Public** key for frontend auth. |

---

## 7. Supabase Setup (VERY IMPORTANT)

Supabase is used for user authentication and file storage. Follow these steps exactly:

1. **Create a Project:** Sign up at [Supabase.com](https://supabase.com/).
2. **Setup Storage:**
    - Go to **Storage** → **New Bucket**.
    - Name: `reports`.
    - Public: **Private** (Recommended for medical data).
3. **Get API Keys:**
    - Go to **Project Settings** → **API**.
    - **service_role key:** Use this for `SUPABASE_SERVICE_ROLE_KEY`. (✅ Correct)
    - **sb_secret:** ❌ **WRONG**. Do not use this; it will cause auth failures.

---

## 8. Running the App

Run the following commands to initialize and start the entire system:

```bash
# 1. Clean up and build containers
docker-compose down -v
docker-compose up --build -d

# 2. Run Database Migrations
# (Sets up all required tables automatically)
docker-compose exec backend alembic upgrade head
```

### Services Started

- **backend:** Port 8000 (API)
- **frontend:** Port 5173 (Web UI)
- **celery-worker:** Handles background AI tasks
- **postgres:** Primary data store
- **redis:** Message queue for Celery tasks
- **prediction-service:** ML prediction node

---

## 9. How to Use

1. Navigate to `http://localhost:5173`.
2. Create an account and log in.
3. Go to the **Reports** section.
4. Upload a medical report (PDF/JPG).
5. Wait a few seconds for the AI to parse the data.
6. View your updated **Health Score** and **Timeline**!

---

## 10. Common Errors (REAL WORLD FIXES)

- **Invalid API Key:** Occurs if you use the `anon` key instead of the `service_role` key in the backend `.env`.
- **Bucket Not Found:** Ensure `SUPABASE_BUCKET_NAME` exactly matches the bucket name you created in the Supabase Dashboard.
- **Migration Deadlock:** Fixed. We ensured that migrations only run from the main backend container, not the celery workers.
- **Postgres Connection Failed:** Docker may need a moment. Run `docker-compose logs -f postgres` to check if it's healthy.

---

## 11. Future Improvements

- **Supabase DB Migration:** Move metadata storage fully to Supabase.
- **Mobile Integration:** Dedicated React Native application.
- **Real-time Engine:** WebSocket-based live ingestion updates.

---

Built with ❤️ by the ArogyaAI Team.
