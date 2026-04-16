"""Utility helpers for the orchestration pipeline."""

from __future__ import annotations


def build_orchestration_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "orchestration_pipeline",
        "mode": "celery_chain",
    }
