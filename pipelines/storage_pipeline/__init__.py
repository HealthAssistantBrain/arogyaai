"""Storage pipeline package."""

from __future__ import annotations

__all__ = [
    "StoragePipelineRequest",
    "StoragePipelineResponse",
    "StoragePipelineService",
    "build_storage_pipeline_context",
]


def __getattr__(name: str):
    if name in {"StoragePipelineRequest", "StoragePipelineResponse"}:
        from .schema import StoragePipelineRequest, StoragePipelineResponse

        mapping = {
            "StoragePipelineRequest": StoragePipelineRequest,
            "StoragePipelineResponse": StoragePipelineResponse,
        }
        return mapping[name]

    if name == "StoragePipelineService":
        from .service import StoragePipelineService

        return StoragePipelineService

    if name == "build_storage_pipeline_context":
        from .utils import build_storage_pipeline_context

        return build_storage_pipeline_context

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
