"""
core/pipeline_logger.py
-----------------------
Structured terminal logger for ArogyaAI pipeline observability.

Usage:
    from core.pipeline_logger import log_pipeline

    log_pipeline("ingestion", step="fetching_data", status="running", data="pending")
    log_pipeline("ingestion", status="healthy", data="fetched")
    log_pipeline("ml",        status="unhealthy", data="failed")

Output format:
    [PIPELINE] ingestion | step=fetching_data | status=running | data=pending
"""
from __future__ import annotations

import logging

# ── Logger setup ──────────────────────────────────────────────────────────────
# Use a dedicated logger so pipeline logs can be filtered independently from
# the main uvicorn/application logs.  A StreamHandler is added only if none
# exists yet (prevents duplicate handlers on auto-reload).
_PIPELINE_LOGGER_NAME = "pipeline_monitor"

pipeline_logger = logging.getLogger(_PIPELINE_LOGGER_NAME)

if not pipeline_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            "[PIPELINE] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    pipeline_logger.addHandler(_handler)

pipeline_logger.setLevel(logging.INFO)
# Prevent messages from bubbling to the root logger and doubling output
pipeline_logger.propagate = False


# ── Public helper ─────────────────────────────────────────────────────────────

def log_pipeline(
    name: str,
    *,
    step: str = "",
    status: str = "",
    data: str = "",
    extra: str = "",
) -> None:
    """
    Emit a structured pipeline log line.

    Args:
        name:   Pipeline identifier (e.g. "ingestion", "ml", "lab").
        step:   Current step label within the pipeline.
        status: "running" | "healthy" | "unhealthy" | any descriptive string.
        data:   Data availability state ("pending" | "fetched" | "failed" | "").
        extra:  Optional free-form suffix for additional context.
    """
    parts: list[str] = [f"{name:<10}"]  # left-aligned name column

    if step:
        parts.append(f"step={step}")
    if status:
        parts.append(f"status={status}")
    if data:
        parts.append(f"data={data}")
    if extra:
        parts.append(extra)

    pipeline_logger.info(" | ".join(parts))


def log_pipeline_section(title: str) -> None:
    """Emit a visual separator in the pipeline log stream."""
    pipeline_logger.info("─" * 8 + f" {title} " + "─" * 8)
