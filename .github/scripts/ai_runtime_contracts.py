#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
for candidate in (REPO_ROOT, BACKEND_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)


class FailingProvider:
    name = "nvidia"
    model = "nvidia-ci"

    def static_models(self) -> list[str]:
        return [self.model]

    async def generate(self, request, *, model: str):
        raise RuntimeError("simulated provider outage")

    async def structured_generate(self, request, *, model: str):
        raise RuntimeError("simulated provider outage")

    async def health(self):
        return {"status": "down"}

    async def healthcheck(self):
        return {"status": "down", "provider": self.name}

    async def available_models(self):
        return [self.model]

    def supports_streaming(self) -> bool:
        return False


class PassingProvider:
    name = "ollama"
    model = "ollama-ci"

    def static_models(self) -> list[str]:
        return [self.model]

    async def generate(self, request, *, model: str):
        payload = {"message": "Fallback response", "recommendations": ["Monitor symptoms."]}
        return {"content": payload, "text": payload["message"], "tokens": {"prompt_tokens": 4, "completion_tokens": 4}}

    async def structured_generate(self, request, *, model: str):
        return await self.generate(request, model=model)

    async def health(self):
        return {"status": "ok"}

    async def healthcheck(self):
        return {"status": "ok", "provider": self.name}

    async def available_models(self):
        return [self.model]

    def supports_streaming(self) -> bool:
        return False


async def validate_provider_fallback() -> None:
    from ai.providers.runtime.provider_runtime import ProviderRuntime
    from ai.providers.models.payloads import ProviderRequest
    from pipelines.rag_pipeline.config import RagSettings

    runtime = ProviderRuntime(RagSettings())
    runtime.registry.providers = {
        "nvidia": FailingProvider(),
        "ollama": PassingProvider(),
    }
    response = await runtime.execute(
        ProviderRequest.from_legacy(
            task="symptom_reasoning",
            workflow="symptom_analysis",
            prompt="CI fallback check",
            system_prompt="Return JSON.",
            context={"severity": "medium"},
        )
    )
    if response.provider != "ollama" or not response.fallback_used:
        fail("Provider runtime did not fall back from NVIDIA to Ollama deterministically.")


def validate_safety_and_recommendations() -> None:
    from ai.providers.models.payloads import ProviderRequest, ProviderResponse
    from ai.providers.validation.safety import MedicalSafetyValidator
    from services.recommendation_service import RecommendationSignals, _build_recommendations

    validator = MedicalSafetyValidator()
    response = ProviderResponse(
        success=True,
        provider="ollama",
        model="llama3.1:8b",
        task="chat_assistant",
        workflow="chatbot",
        status="ready",
        content={"message": "You definitely have a disease.", "confidence_score": 0.99},
        text="You definitely have a disease.",
        confidence=0.99,
    )
    request = ProviderRequest.from_legacy(
        task="chat_assistant",
        workflow="chatbot",
        context={"query": "Do I have a disease?"},
    )
    validated = validator.validate(response, request)
    if not validated.content.get("safety"):
        fail("Medical safety validator did not attach safety metadata.")

    plans = _build_recommendations(
        RecommendationSignals(
            disease_probabilities={"diabetes": 0.72, "cardiovascular": 0.67},
            drivers=[{"label": "High BMI", "domains": ["diabetes"], "contribution": 0.22}],
            has_ml=True,
        )
    )
    if not plans:
        fail("Recommendation generation returned no deterministic plans.")


def validate_scoring_and_ocr_imports() -> None:
    modules = [
        "ai.scoring.core.scoring_engine",
        "ai.scoring.analytics.anomaly_detector",
        "services.lab_pipeline_service",
        "integrations.ocr_service",
        "services.ollama_client",
        "pipelines.rag_pipeline.retriever",
    ]
    for module in modules:
        __import__(module)


def main() -> int:
    asyncio.run(validate_provider_fallback())
    validate_safety_and_recommendations()
    validate_scoring_and_ocr_imports()
    print("[AI_RUNTIME] Provider fallback, safety, recommendation, scoring, OCR, and RAG contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
