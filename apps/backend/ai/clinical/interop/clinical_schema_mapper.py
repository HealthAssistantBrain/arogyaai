from __future__ import annotations

from typing import Any


class ClinicalSchemaMapper:
    @staticmethod
    def to_frontend(payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload or {})
