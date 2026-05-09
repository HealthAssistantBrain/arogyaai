# Environment Setup

## Core analytics variables

Add these to the root `.env`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@postgres:5432/arogyaai

ANALYTICS_DB_MODE=primary
NEON_DATABASE_URL=
NEON_DIRECT_URL=
TIMESCALE_ENABLED=true
ANALYTICS_DB_READ_FALLBACK=true
RUN_ANALYTICS_MIGRATIONS=false
ANALYTICS_WAIT_RETRIES=15
ANALYTICS_WAIT_SLEEP_SECONDS=2
```

For non-Docker backend development, duplicate the same analytics values in `apps/backend/.env`.

## Mode reference

### Local default

Use when Neon is not configured yet:

```env
ANALYTICS_DB_MODE=primary
RUN_ANALYTICS_MIGRATIONS=false
```

Behavior:

- local Timescale container remains the analytics store
- no Neon dependency

### Staging mirror mode

Use while validating a fresh Neon environment:

```env
ANALYTICS_DB_MODE=dual_write
NEON_DATABASE_URL=<pooled Neon URL>
NEON_DIRECT_URL=<direct Neon URL>
RUN_ANALYTICS_MIGRATIONS=true
```

Behavior:

- reads stay on the primary database
- mirrored writes go to Neon
- safe for staged validation and rollback

### Full analytics cutover

Use after validation:

```env
ANALYTICS_DB_MODE=analytics
NEON_DATABASE_URL=<pooled Neon URL>
NEON_DIRECT_URL=<direct Neon URL>
RUN_ANALYTICS_MIGRATIONS=true
```

Behavior:

- analytics reads and writes use Neon
- primary DB remains transactional

## Docker usage

The root `.env` is already loaded by Docker Compose.

Analytics migration run:

```bash
RUN_ANALYTICS_MIGRATIONS=true docker compose up --build
```

Standard start after migrations exist:

```bash
docker compose up --build
```

## Local backend usage

```bash
cd apps/backend
pip install -r requirements.txt
alembic upgrade head
alembic -c alembic_analytics.ini upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Connection validation

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/neon
curl http://localhost:8000/health/timescale
```

## Security notes

- Never hardcode Neon URLs in source code.
- Keep credentials only in `.env`, secret managers, or deployment environment variables.
- Keep `sslmode=require` on both pooled and direct Neon URLs.
- Use the pooled URL for app traffic and the direct URL for migrations and session-bound admin operations.
