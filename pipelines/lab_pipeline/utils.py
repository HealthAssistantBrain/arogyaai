"""Utility helpers for the lab pipeline."""

from __future__ import annotations


def build_lab_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "lab_pipeline",
        "mode": "biomarker_extraction",
    }
