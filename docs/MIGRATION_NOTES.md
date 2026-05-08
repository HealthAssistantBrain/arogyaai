# Migration Notes

## Scope completed

This pass implemented the Step 1A + Step 1B + Step 1C stabilization work for the cloud-collaboration migration:

- auth consolidation
- storage hardening
- profile normalization

The implementation was done incrementally and kept existing routes/adapters in place where they were still needed.

## What changed

### Auth

- Added shared Supabase-only auth dependencies in `apps/backend/core/auth.py`
- Added canonical domain profile route `GET /api/v1/profile`
- Switched frontend email login to Supabase `signInWithPassword`
- Removed frontend reliance on backend `/auth/refresh-token`
- Kept deprecated backend auth endpoints as explicit `410 Gone` markers

### Storage

- New report uploads now persist a private storage reference instead of a permanent public URL
- Added `GET /api/v1/reports/{report_id}/access` for signed temporary access
- Added MIME validation and preserved duplicate-hash protection
- Preserved compatibility for legacy rows that still contain public URLs

### Profile

- Added canonical backend bundle serializer in `apps/backend/services/profile_service.py`
- Added canonical frontend store in `apps/frontend/src/store/profileStore.js`
- Reworked `useUserStore` into a compatibility adapter backed by the canonical profile bundle
- Kept `useAuthStore` state shape stable while syncing it from the canonical profile store

## New environment requirements

Added/documented:

- `SUPABASE_JWT_ISSUER`
- `SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS`

Still required:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `JWT_SECRET_KEY`
- `APP_ENCRYPTION_KEY`

## Deprecated but intentionally retained

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/refresh-token`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/oauth`
- `PUT /api/v1/auth/update-password`
- `REPORT_UPLOAD_DIR` env variable for legacy cleanup compatibility

## Validation completed

Automated validation run during this pass:

- backend: `python -m pytest tests/test_supabase_storage.py tests/test_report_upload_lab_pipeline.py -q`
- backend: `python -m pytest tests/test_notification_preferences_service.py tests/test_timeline_route.py -q`
- frontend: `npm run build`

## Manual smoke tests still recommended

These were not fully exercised end-to-end in a live browser/backend session during this pass:

- signup with verification email
- login/logout through the full UI
- onboarding redirect progression
- report upload + preview + signed access + OCR completion
- secure cross-user access rejection
- expired signed URL rejection in a live Supabase environment

## Rollback considerations

Safe rollback points:

- keep the new `/api/v1/profile` route even if no callers use it yet
- keep deprecated auth endpoints returning `410` instead of deleting them
- keep signed access endpoint even if legacy public URLs remain in old rows

Higher-risk rollback actions:

- reintroducing backend token issuance
- switching report persistence back to public Supabase URLs
- removing `profileStore` before old consumers are fully migrated
