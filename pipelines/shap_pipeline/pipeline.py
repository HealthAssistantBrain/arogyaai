"""Entry point scaffold for the SHAP pipeline."""

from .explainer import ShapExplainer
from .schema import ShapPipelineRequest, ShapPipelineResponse
from .service import ShapPipelineService
from .utils import build_shap_pipeline_context

__all__ = [
    "ShapExplainer",
    "ShapPipelineRequest",
    "ShapPipelineResponse",
    "ShapPipelineService",
    "build_shap_pipeline_context",
]

