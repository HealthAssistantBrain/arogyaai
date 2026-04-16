"""Lab pipeline service wrapper."""

from __future__ import annotations

from .pipeline import run_lab_pipeline


class LabPipelineService:
    run_lab_pipeline = staticmethod(run_lab_pipeline)
