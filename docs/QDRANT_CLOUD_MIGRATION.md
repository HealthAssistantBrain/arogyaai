## Qdrant Cloud Migration

This change adds an environment-driven Qdrant runtime that supports both:

- local Docker Qdrant
- Qdrant Cloud with API key auth and local fallback

### Environment template

```env
QDRANT_MODE=local
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION_MEDICAL=medical_knowledge
LOCAL_QDRANT_URL=http://qdrant:6333

QDRANT_TIMEOUT_SECONDS=5.0
QDRANT_DISTANCE_METRIC=cosine
QDRANT_REQUEST_RETRIES=2
QDRANT_RETRY_BACKOFF_SECONDS=0.75
QDRANT_UNHEALTHY_COOLDOWN_SECONDS=20
QDRANT_UPSERT_BATCH_SIZE=128
QDRANT_LOCAL_FALLBACK_ENABLED=true
```

### Mode behavior

- `QDRANT_MODE=local`: the platform uses `LOCAL_QDRANT_URL`.
- `QDRANT_MODE=cloud`: the platform uses `QDRANT_URL` with `QDRANT_API_KEY`.
- If cloud mode is enabled and the cloud target fails, the runtime can fall back to `LOCAL_QDRANT_URL` when `QDRANT_LOCAL_FALLBACK_ENABLED=true`.

### Health endpoints

- `/health/qdrant`
- `/api/v1/health/qdrant`

Response states:

- `healthy`: connectivity, collection metadata, and query validation succeeded
- `degraded`: collection missing, query validation degraded, or local fallback is active
- `offline`: cloud/local connection could not be established

### Migration script

Run from the repository root after setting the cloud variables:

```bash
python scripts/migrate_qdrant_to_cloud.py --output-json
```

Useful flags:

- `--collection medical_knowledge`
- `--batch-size 128`
- `--force-recreate`
- `--local-url http://localhost:6333`
- `--cloud-url https://<cluster>.cloud.qdrant.io`

The script:

1. reads local collections
2. inspects vector size and distance metric
3. recreates or aligns cloud collections
4. copies points in batches
5. validates counts
6. runs a vector retrieval check in the destination collection

### Collection compatibility

The runtime preserves:

- collection name
- embedding dimensions
- distance metric
- payload contents
- point IDs

Current default medical collection:

- collection: `medical_knowledge`
- embedding dimension: `384`
- distance metric: `cosine`

### Rollback

To roll back to local Docker Qdrant:

1. set `QDRANT_MODE=local`
2. set `LOCAL_QDRANT_URL` to the local service URL
3. leave `QDRANT_URL` and `QDRANT_API_KEY` unset or unused
4. restart backend workers and services

If cloud mode is active but unstable, keeping `QDRANT_LOCAL_FALLBACK_ENABLED=true` allows the backend to continue serving RAG flows from the local store while `/health/qdrant` reports a degraded state.

### Deployment notes

- `docker compose up --build` still works with no cloud credentials when `QDRANT_MODE=local`.
- Cloud mode does not remove the local `qdrant` container; that preserves current development workflows and gives the backend a local fallback target.
- No embedding model or vector dimension changes are required for this migration.
