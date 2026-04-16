"""Utility helpers for the baseline pipeline."""

from __future__ import annotations


def build_baseline_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "baseline_pipeline",
        "mode": "rolling_metrics",
    }
