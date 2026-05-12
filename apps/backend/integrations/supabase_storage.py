"""
integrations/supabase_storage.py
=================================
Private Supabase Storage helpers for medical reports.

New uploads are stored in a private bucket and persisted as an internal
`supabase://bucket/path` reference. Legacy rows that still contain public URLs
remain readable through a compatibility fallback.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status

from core.config import settings
from services.supabase_sdk_validation import (
    SupabaseSDKCompatibilityError,
    load_supabase_client_symbols,
)

logger = logging.getLogger(__name__)


class SupabaseStorageError(RuntimeError):
    """Raised when a Supabase Storage operation fails."""


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename or "report")
    return cleaned.strip("-") or "report"


def _get_client() -> Any:
    if not settings.SUPABASE_URL:
        raise SupabaseStorageError("SUPABASE_URL is not configured.")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseStorageError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured. "
            "Local file storage has been removed. "
            "Set this key to enable Supabase Storage."
        )
    try:
        _, create_client = load_supabase_client_symbols()
    except SupabaseSDKCompatibilityError as exc:
        raise SupabaseStorageError(str(exc)) from exc
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _normalize_bucket(bucket_name: str | None = None) -> str:
    return (bucket_name or settings.SUPABASE_BUCKET_NAME or "medical-reports").strip()


def build_storage_reference(storage_path: str, bucket_name: str | None = None) -> str:
    bucket = _normalize_bucket(bucket_name)
    return f"supabase://{bucket}/{str(storage_path).lstrip('/')}"


def parse_storage_reference(reference: str | None, bucket_name: str | None = None) -> tuple[str, str] | None:
    if not reference:
        return None

    value = str(reference).strip()
    if not value:
        return None

    if value.startswith("supabase://"):
        remainder = value[len("supabase://") :]
        bucket, _, path = remainder.partition("/")
        if bucket and path:
            return bucket, path
        return None

    if "://" not in value:
        return _normalize_bucket(bucket_name), value.lstrip("/")

    parsed = urlparse(value)
    path = parsed.path or ""

    # Legacy public bucket URLs:
    # /storage/v1/object/public/<bucket>/<path>
    marker = "/storage/v1/object/public/"
    if marker in path:
        suffix = path.split(marker, 1)[1]
        bucket, _, storage_path = suffix.partition("/")
        if bucket and storage_path:
            return bucket, storage_path

    # Signed URLs can still be normalized when the storage path is encoded in the route:
    # /storage/v1/object/sign/<bucket>/<path>
    signed_marker = "/storage/v1/object/sign/"
    if signed_marker in path:
        suffix = path.split(signed_marker, 1)[1]
        bucket, _, storage_path = suffix.partition("/")
        if bucket and storage_path:
            return bucket, storage_path

    return None


def _content_type_for_filename(original_name: str) -> str:
    ext = original_name.lower().rsplit(".", 1)[-1] if "." in original_name else ""
    return {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }.get(ext, "application/octet-stream")


def upload_report(user_id: Any, original_name: str, file_bytes: bytes) -> tuple[str, str]:
    """
    Upload a file to a private Supabase bucket and return
    `(storage_path, storage_reference)`.
    """
    safe_name = _safe_filename(original_name)
    storage_path = f"{user_id}/{uuid.uuid4()}-{safe_name}"
    bucket = _normalize_bucket()

    try:
        client = _get_client()
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": _content_type_for_filename(original_name)},
        )
        storage_reference = build_storage_reference(storage_path, bucket)
        logger.info(
            "Supabase Storage upload succeeded: bucket=%s path=%s size=%d private=true",
            bucket,
            storage_path,
            len(file_bytes),
        )
        return storage_path, storage_reference
    except SupabaseStorageError:
        raise
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


def create_signed_download_url(
    storage_path: str,
    bucket_name: str | None = None,
    *,
    expires_in: int | None = None,
    download_filename: str | None = None,
) -> dict[str, Any]:
    bucket = _normalize_bucket(bucket_name)
    ttl_seconds = int(expires_in or settings.SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS)

    try:
        client = _get_client()
        payload = client.storage.from_(bucket).create_signed_url(
            storage_path,
            ttl_seconds,
            {"download": download_filename} if download_filename else {},
        )
        signed_url = payload.get("signedURL")
        if not signed_url:
            raise SupabaseStorageError("Supabase did not return a signed URL.")

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        return {
            "bucket": bucket,
            "path": storage_path,
            "url": signed_url,
            "expires_in": ttl_seconds,
            "expires_at": expires_at.isoformat(),
        }
    except SupabaseStorageError:
        raise
    except Exception as exc:
        logger.exception(
            "Supabase signed URL generation failed: bucket=%s path=%s error=%s",
            bucket,
            storage_path,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"File access is temporarily unavailable: {exc}",
        ) from exc


def resolve_secure_file_access(
    *,
    storage_path: str | None = None,
    storage_reference: str | None = None,
    public_url: str | None = None,
    bucket_name: str | None = None,
    expires_in: int | None = None,
    download_filename: str | None = None,
) -> dict[str, Any]:
    resolved = parse_storage_reference(storage_reference, bucket_name)
    if not resolved:
        resolved = parse_storage_reference(storage_path, bucket_name)
    if resolved:
        bucket, object_path = resolved
        return create_signed_download_url(
            object_path,
            bucket,
            expires_in=expires_in,
            download_filename=download_filename,
        )

    legacy_public_url = str(public_url or "").strip()
    if legacy_public_url:
        ttl_seconds = int(expires_in or settings.SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        return {
            "bucket": bucket_name or settings.SUPABASE_BUCKET_NAME,
            "path": None,
            "url": legacy_public_url,
            "expires_in": ttl_seconds,
            "expires_at": expires_at.isoformat(),
            "legacy_public_url": True,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No stored file is available for this report.",
    )


def delete_report(storage_path: str, bucket_name: str | None = None) -> None:
    if not storage_path:
        return

    resolved = parse_storage_reference(storage_path, bucket_name)
    if resolved:
        bucket, object_path = resolved
    else:
        bucket = _normalize_bucket(bucket_name)
        object_path = storage_path

    try:
        client = _get_client()
        client.storage.from_(bucket).remove([object_path])
        logger.info("Supabase Storage delete succeeded: bucket=%s path=%s", bucket, object_path)
    except SupabaseStorageError:
        raise
    except Exception as exc:
        logger.exception(
            "Supabase Storage delete failed: bucket=%s path=%s error=%s",
            bucket,
            object_path,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"File storage is temporarily unavailable: {exc}",
        ) from exc
