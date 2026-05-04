"""
integrations/supabase_storage.py
=================================
Drop-in replacement for the old local _persist_file() helper.

This module is the ONLY place that knows about Supabase Storage.
Both services (ReportService and report_analysis_service) call
upload_report() and receive the same (storage_path, public_url) tuple
that the old disk-based helper returned — so nothing downstream changes.

Bucket: configured by SUPABASE_BUCKET_NAME (default: "medical-reports")
Auth:   uses SUPABASE_SERVICE_ROLE_KEY to bypass Row Level Security
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from supabase import create_client, Client

from core.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageError(RuntimeError):
    """Raised when a Supabase Storage operation fails."""


def _safe_filename(filename: str) -> str:
    """Sanitise a filename for use as a Supabase object path segment."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename or "report")
    return cleaned.strip("-") or "report"


def _get_client() -> Client:
    """
    Create and return a Supabase client using the service-role key.
    The service-role key grants full storage access and bypasses RLS,
    which is required for server-side uploads.
    """
    if not settings.SUPABASE_URL:
        raise SupabaseStorageError("SUPABASE_URL is not configured.")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseStorageError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured. "
            "Local file storage has been removed. "
            "Set this key to enable Supabase Storage."
        )

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def upload_report(user_id: Any, original_name: str, file_bytes: bytes) -> tuple[str, str]:
    """
    Upload a file to Supabase Storage and return the (storage_path, public_url) tuple.

    This is the **only** method external code should call.
    The signature is intentionally identical to the old _persist_file() helper
    so that callers require zero changes beyond swapping the import.

    Args:
        user_id:       User UUID (used as the first path segment in the bucket).
        original_name: Original filename from the upload, e.g. "blood_test.pdf".
        file_bytes:    Raw byte content of the file.

    Returns:
        (storage_path, public_url)
        - storage_path: Supabase object path, e.g. "<user_id>/<uuid>-blood_test.pdf"
        - public_url:   Full HTTPS URL to the public file, e.g.
                        "https://<project>.supabase.co/storage/v1/object/public/medical-reports/..."
    """
    safe_name = _safe_filename(original_name)
    storage_path = f"{user_id}/{uuid.uuid4()}-{safe_name}"
    bucket = settings.SUPABASE_BUCKET_NAME

    try:
        client = _get_client()

        # Determine content type from extension for correct Content-Type header
        ext = original_name.lower().rsplit(".", 1)[-1] if "." in original_name else ""
        content_type_map = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }
        content_type = content_type_map.get(ext, "application/octet-stream")

        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )

        public_url: str = client.storage.from_(bucket).get_public_url(storage_path)

        logger.info(
            "Supabase Storage upload succeeded: bucket=%s path=%s size=%d",
            bucket,
            storage_path,
            len(file_bytes),
        )

        return storage_path, public_url

    except SupabaseStorageError:
        raise  # re-raise our own errors without wrapping
    except Exception as exc:
        logger.exception(
            "Supabase Storage upload failed: bucket=%s path=%s error=%s",
            bucket,
            storage_path,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"File storage is temporarily unavailable: {exc}",
        ) from exc


def delete_report(storage_path: str, bucket_name: str | None = None) -> None:
    """
    Delete a report object from Supabase Storage.

    Missing or blank paths are treated as a no-op so callers can safely clean up
    legacy rows that were created before storage_path was available.
    """
    if not storage_path:
        return

    bucket = bucket_name or settings.SUPABASE_BUCKET_NAME

    try:
        client = _get_client()
        client.storage.from_(bucket).remove([storage_path])
        logger.info("Supabase Storage delete succeeded: bucket=%s path=%s", bucket, storage_path)
    except SupabaseStorageError:
        raise
    except Exception as exc:
        logger.exception(
            "Supabase Storage delete failed: bucket=%s path=%s error=%s",
            bucket,
            storage_path,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"File storage is temporarily unavailable: {exc}",
        ) from exc
