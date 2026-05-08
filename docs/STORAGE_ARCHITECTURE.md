# Storage Architecture

## Goal

Medical reports are now stored as private Supabase objects instead of permanent public URLs.

## New storage model

New uploads use:

- private Supabase bucket access through the backend service role
- object path persistence in `reports.storage_path`
- internal storage reference persistence in `reports.file_url` as `supabase://<bucket>/<path>`
- compatibility metadata in `summary_data.upload_metadata`

This means `reports.file_url` is no longer treated as a browser-safe public URL for newly uploaded rows.

## Secure access flow

New secure access pattern:

1. frontend requests `GET /api/v1/reports/{report_id}/access`
2. backend verifies ownership through the authenticated domain user
3. backend generates a temporary signed Supabase URL
4. frontend uses that temporary URL for preview/download

Response shape:

```json
{
  "success": true,
  "status": "ready",
  "data": {
    "report_id": "...",
    "file_name": "cbc-report.pdf",
    "url": "https://...signed...",
    "expires_at": "2026-05-08T12:34:56+00:00",
    "expires_in": 900,
    "legacy_public_url": false
  }
}
```

## Upload hardening

The upload path now enforces:

- extension validation: `.pdf`, `.jpg`, `.jpeg`, `.png`
- MIME validation against the extension
- file-size validation through `ReportService.MAX_FILE_SIZE_BYTES`
- filename sanitization before object creation
- duplicate file detection through `reports.user_id + file_hash`

The OCR pipeline, background processing, lab extraction, and timeline creation were preserved.

## Backward compatibility

Legacy rows that still contain public URLs remain readable.

Compatibility behavior:

- legacy public URLs are still parsed and returned as a fallback access URL
- delete logic still tolerates old local-path/public-url assumptions
- report serialization exposes `file_access_required` so the frontend can request dynamic access instead of assuming `file_url` is directly embeddable

## Frontend behavior

Report preview now behaves like this:

- use `localPreviewUrl` for optimistic/local previews
- use persisted `fileUrl` only for legacy public rows
- otherwise resolve `GET /api/v1/reports/{id}/access` on demand

The summary PDF route `GET /api/v1/reports/{id}/download` remains unchanged and still returns the generated clinical PDF, not the original uploaded file.

## Environment

New backend/runtime knobs:

- `SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS`
- `SUPABASE_BUCKET_NAME`
- `SUPABASE_SERVICE_ROLE_KEY`

`REPORT_UPLOAD_DIR` remains in env templates only as a deprecated fallback marker for old cleanup logic.
