"""
tests/test_supabase_storage.py
=================================
Regression tests for the private Supabase Storage integration module.

Run with:
    cd apps/backend && python -m pytest tests/test_supabase_storage.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


FAKE_SUPABASE_URL = "https://testproject.supabase.co"
FAKE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.service_role_test"
FAKE_BUCKET = "medical-reports"
FAKE_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
FAKE_FILENAME = "blood_test.pdf"
FAKE_BYTES = b"%PDF-1.4 fake content"


@pytest.fixture(autouse=True)
def patch_settings():
    with patch("integrations.supabase_storage.settings") as mock_settings:
        mock_settings.SUPABASE_URL = FAKE_SUPABASE_URL
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = FAKE_SERVICE_KEY
        mock_settings.SUPABASE_BUCKET_NAME = FAKE_BUCKET
        mock_settings.SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS = 900
        yield mock_settings


class TestUploadReport:
    def test_upload_returns_private_storage_reference(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, storage_reference = upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        assert storage_path.startswith(str(FAKE_USER_ID))
        assert storage_path.endswith("blood_test.pdf")
        assert storage_reference == f"supabase://{FAKE_BUCKET}/{storage_path}"
        assert "object/public" not in storage_reference

    def test_upload_calls_supabase_with_correct_bucket(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        mock_client.storage.from_.assert_called_once_with(FAKE_BUCKET)
        mock_storage_bucket.upload.assert_called_once()

    def test_upload_uses_correct_content_type_for_pdf(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            upload_report(FAKE_USER_ID, "report.pdf", FAKE_BYTES)

        call_kwargs = mock_storage_bucket.upload.call_args[1]
        assert call_kwargs["file_options"]["content-type"] == "application/pdf"

    def test_upload_failure_raises_http_exception(self):
        from fastapi import HTTPException

        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.side_effect = RuntimeError("S3 connection refused")

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            with pytest.raises(HTTPException) as exc_info:
                upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        assert exc_info.value.status_code == 503
        assert "storage is temporarily unavailable" in exc_info.value.detail

    def test_missing_service_key_raises_storage_error(self):
        with patch("integrations.supabase_storage.settings") as mock_settings:
            mock_settings.SUPABASE_URL = FAKE_SUPABASE_URL
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = ""
            mock_settings.SUPABASE_BUCKET_NAME = FAKE_BUCKET
            mock_settings.SUPABASE_STORAGE_SIGNED_URL_TTL_SECONDS = 900

            from integrations.supabase_storage import SupabaseStorageError, upload_report

            with pytest.raises(SupabaseStorageError, match="SUPABASE_SERVICE_ROLE_KEY"):
                upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

    def test_safe_filename_strips_special_chars(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        weird_name = "blood test (2024) #1 report!.pdf"

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, _ = upload_report(FAKE_USER_ID, weird_name, FAKE_BYTES)

        path_filename = storage_path.split("/", 1)[1]
        assert " " not in path_filename
        assert "#" not in path_filename
        assert "!" not in path_filename
        assert "(" not in path_filename

    def test_upload_return_type_matches_old_persist_file_contract(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, storage_reference = upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        assert isinstance(storage_path, str)
        assert isinstance(storage_reference, str)


class TestSignedUrls:
    def test_create_signed_download_url_returns_temporary_url(self):
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.create_signed_url.return_value = {
            "signedURL": f"{FAKE_SUPABASE_URL}/storage/v1/object/sign/{FAKE_BUCKET}/{FAKE_USER_ID}/abc.pdf?token=test"
        }
        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import create_signed_download_url

            result = create_signed_download_url(f"{FAKE_USER_ID}/abc.pdf", FAKE_BUCKET, expires_in=300)

        assert result["url"].startswith(FAKE_SUPABASE_URL)
        assert result["expires_in"] == 300

    def test_resolve_secure_file_access_uses_legacy_public_url_when_needed(self):
        from integrations.supabase_storage import resolve_secure_file_access

        result = resolve_secure_file_access(
            public_url=f"{FAKE_SUPABASE_URL}/storage/v1/object/public/{FAKE_BUCKET}/{FAKE_USER_ID}/abc.pdf"
        )

        assert result["url"].startswith(FAKE_SUPABASE_URL)
        assert result["legacy_public_url"] is True
