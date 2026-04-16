"""Utility helpers for the storage pipeline."""

from __future__ import annotations


def build_storage_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "storage_pipeline",
        "mode": "db_write",
    }
