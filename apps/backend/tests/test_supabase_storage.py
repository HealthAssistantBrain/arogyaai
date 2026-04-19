"""
tests/test_supabase_storage.py
=================================
Regression tests for the Supabase Storage integration module.

Run with:
    cd apps/backend && python -m pytest tests/test_supabase_storage.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


FAKE_SUPABASE_URL = "https://testproject.supabase.co"
FAKE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.service_role_test"
FAKE_BUCKET = "medical-reports"
FAKE_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
FAKE_FILENAME = "blood_test.pdf"
FAKE_BYTES = b"%PDF-1.4 fake content"


@pytest.fixture(autouse=True)
def patch_settings():
    """Inject fake Supabase credentials so tests don't need real config."""
    with patch("integrations.supabase_storage.settings") as mock_settings:
        mock_settings.SUPABASE_URL = FAKE_SUPABASE_URL
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = FAKE_SERVICE_KEY
        mock_settings.SUPABASE_BUCKET_NAME = FAKE_BUCKET
        yield mock_settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUploadReport:
    """Tests for the upload_report() function."""

    def test_upload_returns_valid_storage_path_and_url(self):
        """Happy path: upload returns a (storage_path, public_url) tuple."""
        expected_public_url = (
            f"{FAKE_SUPABASE_URL}/storage/v1/object/public/"
            f"{FAKE_BUCKET}/{FAKE_USER_ID}/some-uuid-blood_test.pdf"
        )

        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.get_public_url.return_value = expected_public_url

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, public_url = upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        # storage_path should be "<user_id>/<uuid>-<safe_name>"
        assert storage_path.startswith(str(FAKE_USER_ID))
        assert storage_path.endswith("blood_test.pdf")

        # public_url should be exactly what Supabase returned
        assert public_url == expected_public_url
        assert "supabase.co" in public_url

    def test_upload_calls_supabase_with_correct_bucket(self):
        """The upload() call must target the configured bucket."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.get_public_url.return_value = "https://test.supabase.co/some-url"

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        # from_() is called twice: once for upload and once for get_public_url
        # Both calls must use the correct bucket name
        mock_client.storage.from_.assert_any_call(FAKE_BUCKET)
        assert mock_client.storage.from_.call_count == 2
        mock_storage_bucket.upload.assert_called_once()

    def test_upload_uses_correct_content_type_for_pdf(self):
        """PDF files should be uploaded with application/pdf content-type."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.get_public_url.return_value = "https://x.supabase.co/url"

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            upload_report(FAKE_USER_ID, "report.pdf", FAKE_BYTES)

        _call_kwargs = mock_storage_bucket.upload.call_args[1]
        assert _call_kwargs["file_options"]["content-type"] == "application/pdf"

    def test_upload_failure_raises_http_exception(self):
        """A storage SDK error should be converted to a 503 HTTPException."""
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
        """Missing service role key should raise SupabaseStorageError, not 500."""
        with patch("integrations.supabase_storage.settings") as mock_settings:
            mock_settings.SUPABASE_URL = FAKE_SUPABASE_URL
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = ""  # missing!
            mock_settings.SUPABASE_BUCKET_NAME = FAKE_BUCKET

            from integrations.supabase_storage import upload_report, SupabaseStorageError

            with pytest.raises(SupabaseStorageError, match="SUPABASE_SERVICE_ROLE_KEY"):
                upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

    def test_safe_filename_strips_special_chars(self):
        """Filenames with special characters must be sanitised before upload."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.get_public_url.return_value = "https://test.supabase.co/url"

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        weird_name = "blood test (2024) #1 report!.pdf"

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, _ = upload_report(FAKE_USER_ID, weird_name, FAKE_BYTES)

        # Path should NOT contain spaces, parentheses, or hash symbols
        path_filename = storage_path.split("/", 1)[1]  # strip user_id prefix
        assert " " not in path_filename
        assert "#" not in path_filename
        assert "!" not in path_filename
        assert "(" not in path_filename

    def test_upload_return_type_matches_old_persist_file_contract(self):
        """
        Critical: upload_report() must return (str, str) — previously (Path, str).
        All callers that use storage_path as a string must work.
        """
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.get_public_url.return_value = "https://proj.supabase.co/obj"

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_storage_bucket

        with patch("integrations.supabase_storage.create_client", return_value=mock_client):
            from integrations.supabase_storage import upload_report

            storage_path, public_url = upload_report(FAKE_USER_ID, FAKE_FILENAME, FAKE_BYTES)

        assert isinstance(storage_path, str)
        assert isinstance(public_url, str)
