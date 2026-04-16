"""Utility helpers for the SHAP pipeline."""

from __future__ import annotations


def build_shap_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "shap_pipeline",
        "mode": "conditional_explainability",
    }
