from __future__ import annotations

from pipelines.rag_pipeline.config import RagSettings

from ..runtime.provider_runtime import ProviderRuntime

_RUNTIME: ProviderRuntime | None = None


def get_provider_runtime(settings: RagSettings | None = None) -> ProviderRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = ProviderRuntime(settings=settings)
    return _RUNTIME
