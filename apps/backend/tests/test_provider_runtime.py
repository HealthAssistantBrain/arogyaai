from __future__ import annotations

import asyncio
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.providers.models.payloads import ProviderAttempt, ProviderRequest, ProviderResponse
from ai.providers.runtime.provider_runtime import ProviderRuntime
from pipelines.rag_pipeline.config import RagSettings
from services.orchestrator.model_registry import ModelRegistry


class _FakeProvider:
    def __init__(self, name: str, model: str, *, payload: dict | None = None, error: Exception | None = None):
        self.name = name
        self._model = model
        self.payload = payload or {"message": f"{name} ready", "recommendations": ["Stay hydrated."]}
        self.error = error

    def static_models(self) -> list[str]:
        return [self._model]

    async def generate(self, request, *, model: str):
        if self.error:
            raise self.error
        return {"content": self.payload, "text": self.payload.get("message"), "tokens": {"prompt_tokens": 11, "completion_tokens": 7}}

    async def structured_generate(self, request, *, model: str):
        return await self.generate(request, model=model)

    async def healthcheck(self):
        return {"status": "ok", "provider": self.name}

    async def available_models(self):
        return [self._model]

    def supports_streaming(self) -> bool:
        return False


def test_provider_runtime_falls_back_from_nvidia_to_ollama():
    runtime = ProviderRuntime(RagSettings())
    runtime.registry.providers = {
        "nvidia": _FakeProvider("nvidia", "nvidia-reasoning", error=RuntimeError("nvidia unavailable")),
        "ollama": _FakeProvider("ollama", "llama3.1:8b", payload={"message": "Fallback response", "recommendations": ["Monitor symptoms."]}),
        "openai": _FakeProvider("openai", "gpt-4o-mini", payload={"message": "OpenAI response"}),
    }

    response = asyncio.run(
        runtime.execute(
            ProviderRequest.from_legacy(
                task="symptom_reasoning",
                workflow="symptom_analysis",
                prompt="Explain chest pain and dizziness",
                system_prompt="Return JSON.",
                context={"severity": "medium"},
            )
        )
    )

    assert response.provider == "ollama"
    assert response.fallback_used is True
    assert response.content["message"] == "Fallback response"
    assert response.attempts[0].provider == "nvidia"
    assert response.attempts[0].status == "failed"
    assert response.attempts[1].provider == "ollama"
    assert response.attempts[1].status == "ready"


def test_model_registry_uses_runtime_by_default(monkeypatch):
    registry = ModelRegistry(RagSettings())

    async def _fake_execute(request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            success=True,
            provider="nvidia",
            model="nvidia-fast",
            task=request.task,
            workflow=request.workflow,
            status="ready",
            content={"message": "runtime ok", "recommendations": ["Follow up if it worsens."]},
            text="runtime ok",
            recommendations=["Follow up if it worsens."],
            confidence=0.72,
            attempts=[ProviderAttempt(provider="nvidia", model="nvidia-fast", status="ready")],
            metadata={"request_id": request.request_id},
        )

    monkeypatch.setattr(registry.runtime, "execute", _fake_execute)

    result = asyncio.run(
        registry.generate_json(
            task="chat_assistant",
            workflow="chatbot",
            prompt="Hello",
            system_prompt="Return JSON only.",
            context={"query": "Hello"},
            metadata={"latency_tier": "interactive"},
        )
    )

    assert result["provider"] == "nvidia"
    assert result["payload"]["message"] == "runtime ok"
    assert result["attempts"][0]["provider"] == "nvidia"
