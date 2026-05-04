"""Compatibility facade for the canonical backend lab pipeline."""
from __future__ import annotations

try:
    from apps.backend.services.lab_pipeline_service import (
        extract_lab_values,
        map_loinc,
        normalize_lab_values,
        run_lab_pipeline,
        store_lab_results,
    )
except ImportError:  # pragma: no cover - backend package path inside container
    from services.lab_pipeline_service import (
        extract_lab_values,
        map_loinc,
        normalize_lab_values,
        run_lab_pipeline,
        store_lab_results,
    )

__all__ = [
    "extract_lab_values",
    "map_loinc",
    "normalize_lab_values",
    "run_lab_pipeline",
    "store_lab_results",
]
