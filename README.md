# ArogyaAI 🧠⚕️

> **Predictive Health Intelligence Platform** — Ingest continuous patient data from wearables, parse medical reports with AI, and deliver ML-powered predictive health insights.

---

## Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/arogyaai.git
cd arogyaai

# 2. Create your environment file
cp .env.template .env

# 3. Fill required values (see "Environment Setup" below)
#    At minimum: SUPABASE_URL, SUPABASE keys, JWT_SECRET_KEY, APP_ENCRYPTION_KEY

# 4. Start the entire stack
docker compose up --build
```

**That's it.** Migrations run automatically. All services start in dependency order with health checks.

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | React Web App |
| **Backend API** | http://localhost:8000 | FastAPI Orchestrator |
| **Swagger Docs** | http://localhost:8000/docs | Interactive API Reference |
| **PgAdmin** | http://localhost:5050 | Database Admin Panel |
| **Prediction Service** | http://localhost:8001 | ML Inference Engine |
| **RAG Service** | http://localhost:8002 | Medical Explanation System |

---

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐
│   React UI  │───▶│  FastAPI      │───▶│  Primary PostgreSQL  │
│   (Zustand) │◀───│  Backend      │◀───│  auth + metadata     │
└─────────────┘    └──────┬───────┘    └──────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         ┌────▼────┐ ┌────▼────┐ ┌────▼──────────────┐
         │Prediction│ │  RAG    │ │ Neon + Timescale │
         │ Service  │ │ Service │ │ vitals + scores  │
         └─────────┘ └─────────┘ └────┬──────────────┘
                                      │
                                 ┌────▼────┐
                                 │  Redis  │
                                 └─────────┘
```

**Data Flow:**
1. **Upload** — User uploads medical report via React UI
2. **Backend** — FastAPI receives file, stores in Supabase Storage
3. **Celery** — Background task triggered for report processing
4. **AI Engine** — Prediction Service performs OCR + risk evaluation
5. **Database** — Extracted metrics and scores saved to PostgreSQL
6. **Dashboard** — UI updates automatically with analysis and trends

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Zustand, Framer Motion, Tailwind CSS, Recharts |
| **Backend** | FastAPI (Python 3.11), Pydantic, SQLAlchemy |
| **Async Processing** | Celery + Redis |
| **Database** | PostgreSQL 15 + TimescaleDB (time-series) |
| **Vector Search** | Qdrant (RAG + medical explanations) |
| **Cloud Storage** | Supabase Storage |
| **Auth** | Supabase Auth + JWT |
| **ML/AI** | OCR, Rule Engines, SHAP Explainability, Ollama/OpenAI |
| **Containerization** | Docker Compose (multi-stage builds) |

---

## Project Structure

```
arogyaai/
├── apps/
│   ├── backend/              # FastAPI orchestrator, core logic & API
│   │   ├── alembic/          # Database migrations
│   │   ├── api/              # Versioned API routes
│   │   ├── core/             # Config, security, middleware
│   │   ├── database/         # SQLAlchemy session & models
│   │   ├── docker/           # Entrypoint scripts, constraints
│   │   ├── models/           # ORM models
│   │   ├── routes/           # Modular API routers
│   │   ├── services/         # Business logic layer
│   │   └── workers/          # Background workers (Google Fit, Emergency)
│   └── frontend/             # React web application
│       ├── src/
│       │   ├── components/   # Reusable UI components
│       │   ├── pages/        # Page-level views
│       │   ├── store/        # Zustand state stores
│       │   ├── services/     # API client services
│       │   └── lib/          # Utilities (axios, supabase)
│       └── public/           # Static assets
├── pipelines/
│   ├── prediction-service/   # ML inference + clinical rule engine
│   ├── rag-service/          # RAG-based medical explanation
│   ├── wearable-service/     # Wearable data normalization
│   └── *_pipeline/           # Specialized data pipelines
├── infra/                    # Nginx, infrastructure configs
├── docs/                     # Technical documentation
├── scripts/                  # Utility scripts
├── .env.template             # ← Copy this to .env
└── docker-compose.yml        # Service orchestration
```

---

## Environment Setup

### Step 1: Copy Template

```bash
cp .env.template .env
```

### Step 2: Fill Required Values

| Variable | Where to Get It | Required? |
|----------|----------------|-----------|
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` | ✅ Yes |
| `APP_ENCRYPTION_KEY` | Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | ✅ Yes |
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API | ✅ Yes |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Project Settings → API → `anon` key | ✅ Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Project Settings → API → `service_role` key | ✅ Yes |
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` | ✅ Yes |
| `VITE_SUPABASE_ANON_KEY` | Same as `SUPABASE_ANON_KEY` | ✅ Yes |
| `GOOGLE_FIT_CLIENT_ID` | See [Google Fit Setup](docs/GOOGLE_FIT_SETUP.md) | Optional |
| `GOOGLE_FIT_CLIENT_SECRET` | See [Google Fit Setup](docs/GOOGLE_FIT_SETUP.md) | Optional |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | Optional |
| `OPENWEATHER_API_KEY` | https://openweathermap.org/api | Optional |

> **⚠️ Important:** The backend will **fail to start** if required variables are missing or contain placeholder values. This is intentional — it prevents running with insecure defaults.

### Step 3: Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Storage** → **New Bucket** → Name: `reports`, Access: **Private**
3. Go to **Project Settings** → **API** to find your keys
4. Use the `service_role` key (NOT `sb_secret`) for `SUPABASE_SERVICE_ROLE_KEY`

### Analytics Migration Docs

- [docs/NEON_SETUP.md](docs/NEON_SETUP.md)
- [docs/TIMESCALE_ARCHITECTURE.md](docs/TIMESCALE_ARCHITECTURE.md)
- [docs/ANALYTICS_DB_GUIDE.md](docs/ANALYTICS_DB_GUIDE.md)
- [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
- [docs/ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)

---

## Running the Application

### Docker (Recommended)

```bash
# Start all services (migrations run automatically)
docker compose up --build

# Start in detached mode
docker compose up --build -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down

# Full reset (removes data volumes)
docker compose down -v
```

### GPU Support (NVIDIA)

```bash
docker compose --profile gpu up --build
```

### Seed Demo Data (Optional)

Preview the dashboard without a wearable device or real reports:

```bash
docker compose exec backend python /app/scripts/seed_demo_data.py
```

---

## Service Health

The backend exposes a health endpoint that checks all dependencies:

```bash
curl http://localhost:8000/health
```

Response shows status of: `db`, `redis`, `prediction_service`, `rag_service`

---

## Development

### Frontend Only (outside Docker)

```bash
cd apps/frontend
npm install
npm run dev
```

### Backend Only (outside Docker)

```bash
cd apps/backend
pip install -r requirements.txt
# Set DATABASE_URL to point to your local postgres
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Migrations Manually

```bash
docker compose exec backend alembic upgrade head
```

---

## Google Fit Integration

See the full setup guide: **[docs/GOOGLE_FIT_SETUP.md](docs/GOOGLE_FIT_SETUP.md)**

Quick summary:
1. Create a Google Cloud project with Fitness API enabled
2. Create OAuth 2.0 credentials (Web Application type)
3. Set redirect URI to `http://localhost:8000/api/v1/google-fit/oauth/callback`
4. Copy Client ID and Client Secret to your `.env` file

---

## Troubleshooting

### Backend won't start — "CRITICAL STARTUP FAILURE"

**Cause:** Required environment variables are missing or contain placeholder values.

**Fix:** Open `.env` and replace all `your_..._here` values with real credentials.

### "Invalid API Key" from Supabase

**Cause:** Using the wrong key type.

**Fix:** Use the `service_role` key (from Project Settings → API), not the `sb_secret` or `anon` key for backend operations.

### Database connection failed

**Cause:** PostgreSQL container isn't ready yet.

**Fix:** Wait 10–15 seconds after `docker compose up`. Check with:
```bash
docker compose logs -f postgres
```

### Frontend shows "Configuration Error"

**Cause:** `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` is missing.

**Fix:** Ensure these are set in the root `.env` file. The Docker Compose passes them to the frontend container.

### Migrations fail

**Cause:** Schema mismatch or stale migration state.

**Fix:**
```bash
docker compose exec backend alembic upgrade head
# If that fails, try stamping to current:
docker compose exec backend alembic stamp head
docker compose exec backend alembic upgrade head
```

### Port conflicts

**Fix:** Change the port mappings in `docker-compose.yml`. Default ports:
- `5173` → Frontend
- `8000` → Backend
- `5432` → PostgreSQL
- `6379` → Redis
- `6333` → Qdrant
- `5050` → PgAdmin

---

## CI/CD

GitHub Actions runs on every push to `master`/`develop`:

1. **Validate** — Docker Compose config check
2. **Build** — Frontend build + Docker image builds + backend health check
3. **Test Backend** — Alembic migrations + pytest
4. **Test ML** — ML pipeline unit tests
5. **Test RAG** — RAG pipeline unit tests
6. **Smoke** — Compile-check prediction/rag/wearable services

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Copy and fill environment: `cp .env.template .env`
4. Start the stack: `docker compose up --build`
5. Make your changes
6. Run tests: `docker compose exec backend python -m pytest`
7. Submit a pull request

> **Never commit `.env` files.** The `.gitignore` prevents this, but always double-check.

---

Built with ❤️ by the ArogyaAI Team.
