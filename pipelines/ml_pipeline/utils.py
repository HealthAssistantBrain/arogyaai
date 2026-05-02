"""Utility helpers for the ML pipeline."""

from __future__ import annotations

from functools import lru_cache
import logging
import os


logger = logging.getLogger("uvicorn.error")


def build_ml_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "ml_pipeline",
        "mode": "hybrid_safe",
    }


def gpu_requested() -> bool:
    return os.getenv("ENABLE_GPU", "").strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def is_gpu_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def should_use_gpu() -> bool:
    requested = gpu_requested()
    available = is_gpu_available() if requested else False
    if requested and available:
        logger.info("ML GPU enabled | backend=xgboost")
        return True
    if requested:
        logger.info("ML GPU requested but unavailable; using CPU fallback")
    else:
        logger.info("ML GPU disabled by ENABLE_GPU; using CPU")
    return False
