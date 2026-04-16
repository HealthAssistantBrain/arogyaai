"""Utility helpers for the feature pipeline."""

from __future__ import annotations


def build_feature_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "feature_pipeline",
        "mode": "store_and_score",
    }
