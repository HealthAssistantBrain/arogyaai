from __future__ import annotations

from typing import Any


def normalize_uploaded_file_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized["filename"] = str(normalized.get("filename") or normalized.get("file_name") or "report").strip()
    normalized["content_type"] = str(normalized.get("content_type") or "").strip() or None
    return normalized

