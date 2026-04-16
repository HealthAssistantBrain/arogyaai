"""Utility helpers for the ML pipeline."""

from __future__ import annotations


def build_ml_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "ml_pipeline",
        "mode": "hybrid_safe",
    }
