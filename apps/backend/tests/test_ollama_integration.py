from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.ollama_client import ollama_generate_json
from services.ollama_client import get_ollama_availability
from services.ollama_client import ollama_provider_enabled
from services.ollama_client import probe_ollama_health
from services.agents.response_agent import _build_response_prompt
from services.orchestrator.model_registry import ModelRegistry
from services.orchestrator.providers.base import BaseAIProvider
from services import ollama_client as ollama_client_module


class _UnavailableProvider(BaseAIProvider):
    name = "unavailable"

    def is_available(self) -> bool:
        return False

    async def generate_json(self, prompt: str, *, system_prompt: str = "", workflow: str = "generic"):
        raise AssertionError("generate_json should not be called when provider is unavailable")


class _FailingProvider(BaseAIProvider):
    name = "failing"

    def is_available(self) -> bool:
        return True

    async def generate_json(self, prompt: str, *, system_prompt: str = "", workflow: str = "generic"):
        raise RuntimeError("provider boom")


class _ReadyProvider(BaseAIProvider):
    name = "ready"

    def is_available(self) -> bool:
        return True

    async def generate_json(self, prompt: str, *, system_prompt: str = "", workflow: str = "generic"):
        return {"message": "ok", "workflow": workflow}


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or ""

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return self.response

    async def get(self, url: str):
        raise AssertionError("GET was not expected in this test")


class _ProbeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _ProbeClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.get_calls = 0

    async def get(self, url: str):
        self.get_calls += 1
        return _ProbeResponse(self.payload)


def _settings(**overrides):
    base = {
        "ollama_base_url": "http://ollama.test:11434",
        "ollama_timeout_seconds": 45.0,
        "ollama_connect_timeout_seconds": 5.0,
        "ollama_keep_alive": "10m",
        "ollama_request_retries": 0,
        "ollama_retry_backoff_seconds": 0.0,
        "ollama_num_ctx": None,
        "ollama_model": "llama3.1:8b",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_model_registry_records_attempts_without_slots_dict_bug(monkeypatch):
    registry = ModelRegistry()
    registry.providers = {
        "local": _FailingProvider(),
        "openai": _ReadyProvider(),
        "nvidia": _UnavailableProvider(),
    }
    monkeypatch.setattr(registry, "provider_order", lambda workflow="generic": ["local", "openai", "nvidia"])

    result = asyncio.run(
        registry.generate_json(
            workflow="chatbot",
            prompt="hello",
            system_prompt="system",
        )
    )

    assert result["provider"] == "openai"
    assert result["payload"]["message"] == "ok"
    assert result["attempts"] == [
        {"provider": "local", "status": "failed", "error": "provider boom"},
        {"provider": "openai", "status": "ready", "error": None},
    ]


def test_ollama_generate_json_uses_system_prompt_and_keep_alive(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            payload={
                "response": '{"message":"hello"}',
                "eval_count": 8,
                "prompt_eval_count": 12,
            }
        )
    )
    monkeypatch.setattr("services.ollama_client._get_async_client", lambda settings: fake_client)
    monkeypatch.setattr("services.ollama_client.persist_ollama_failure", lambda record: None)

    result = asyncio.run(
        ollama_generate_json(
            prompt="user prompt",
            system_prompt="system prompt",
            settings=_settings(),
            model_name="llama3.1:8b",
            workflow="chatbot",
            options={"temperature": 0.1},
        )
    )

    assert result["payload"] == {"message": "hello"}
    assert fake_client.calls[0][0] == "/api/generate"
    sent_payload = fake_client.calls[0][1]
    assert sent_payload["system"] == "system prompt"
    assert sent_payload["prompt"] == "user prompt"
    assert sent_payload["keep_alive"] == "10m"
    assert sent_payload["options"]["temperature"] == 0.1


def test_ollama_generate_json_raises_on_unstructured_response(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            payload={
                "response": "hello world",
                "eval_count": 2,
                "prompt_eval_count": 3,
            }
        )
    )
    failures: list[dict] = []
    monkeypatch.setattr("services.ollama_client._get_async_client", lambda settings: fake_client)
    monkeypatch.setattr("services.ollama_client.persist_ollama_failure", failures.append)

    with pytest.raises(RuntimeError, match="no structured JSON response"):
        asyncio.run(
            ollama_generate_json(
                prompt="user prompt",
                settings=_settings(),
                model_name="llama3.1:8b",
                workflow="chatbot",
            )
        )

    assert failures
    assert failures[0]["workflow"] == "chatbot"
    assert failures[0]["model"] == "llama3.1:8b"


def test_ollama_generate_json_marks_provider_degraded_after_http_500(monkeypatch):
    ollama_client_module._HEALTH_CACHE.clear()
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=500,
            text="internal error",
        )
    )
    failures: list[dict] = []
    settings = _settings()
    monkeypatch.setenv("OLLAMA_PROVIDER_ENABLED", "true")
    monkeypatch.setattr("services.ollama_client._get_async_client", lambda resolved_settings: fake_client)
    monkeypatch.setattr("services.ollama_client.persist_ollama_failure", failures.append)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        asyncio.run(
            ollama_generate_json(
                prompt="user prompt",
                settings=settings,
                model_name="llama3.1:8b",
                workflow="chatbot",
            )
        )

    availability = get_ollama_availability(settings)
    assert failures
    assert availability["routable"] is False
    assert availability["reason"] == "ollama_http_failure"


def test_probe_ollama_health_uses_cached_result(monkeypatch):
    ollama_client_module._HEALTH_CACHE.clear()
    probe_client = _ProbeClient({"models": [{"name": "llama3.1:8b"}]})
    monkeypatch.setenv("OLLAMA_PROVIDER_ENABLED", "true")
    monkeypatch.setattr("services.ollama_client._get_async_client", lambda settings: probe_client)

    first = asyncio.run(probe_ollama_health(_settings()))
    second = asyncio.run(probe_ollama_health(_settings()))

    assert first["status"] == "ok"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert probe_client.get_calls == 1


def test_ollama_provider_can_be_disabled(monkeypatch):
    monkeypatch.setenv("OLLAMA_PROVIDER_ENABLED", "false")

    assert ollama_provider_enabled() is False


def test_ollama_availability_uses_cached_probe_failure(monkeypatch):
    ollama_client_module._HEALTH_CACHE.clear()
    monkeypatch.setenv("OLLAMA_PROVIDER_ENABLED", "true")
    settings = _settings()
    ollama_client_module._store_cached_ollama_health(
        settings,
        {
            "status": "degraded",
            "reason": "ollama_probe_failed",
            "error": "connection refused",
            "cache_hit": False,
        },
    )

    availability = get_ollama_availability(settings)

    assert availability["routable"] is False
    assert availability["reason"] == "ollama_probe_failed"


def test_model_registry_marks_local_provider_unavailable_from_cached_probe(monkeypatch):
    ollama_client_module._HEALTH_CACHE.clear()
    monkeypatch.setenv("OLLAMA_PROVIDER_ENABLED", "true")
    settings = _settings()
    ollama_client_module._store_cached_ollama_health(
        settings,
        {
            "status": "degraded",
            "reason": "ollama_probe_failed",
            "error": "connection refused",
            "cache_hit": False,
        },
    )

    registry = ModelRegistry(settings)
    registry.providers["openai"] = _ReadyProvider()
    registry.providers["nvidia"] = _UnavailableProvider()
    monkeypatch.setattr(registry, "provider_order", lambda workflow="generic": ["local", "openai", "nvidia"])

    result = asyncio.run(
        registry.generate_json(
            workflow="chatbot",
            prompt="hello",
            system_prompt="system",
        )
    )

    assert result["provider"] == "openai"
    assert result["attempts"][0]["provider"] == "local"
    assert result["attempts"][0]["status"] == "unavailable"
    assert result["attempts"][0]["error"] == "ollama_probe_failed"


def test_response_generator_prompt_compacts_large_context():
    huge_notes = "very long note " * 2000
    prompt = _build_response_prompt(
        {
            "query": "Explain my recent symptoms",
            "user_context": {
                "profile": {"age": 52, "gender": "male"},
                "vitals": {"heart_rate": {"latest": 110, "avg_7d": 88, "unit": "bpm"}},
                "abnormal_labs": [{"name": "Glucose", "value": 132, "unit": "mg/dL", "status": "high", "notes": huge_notes}],
                "vital_highlights": [huge_notes],
            },
            "symptoms": {"symptom_names": ["chest pain", "dizziness"], "severity": "high"},
            "ml_interpretation": {"risk_level": "HIGH", "interpretation": huge_notes, "top_drivers": [{"label": "Heart Rate", "direction": "higher than usual"}]},
            "clinical_reasoning": {"clinical_interpretation": huge_notes, "possible_causes": ["cardiovascular strain"], "confidence_score": 0.7},
            "safety": {"risk_level": "HIGH", "requires_immediate_care": True, "safety_notes": [huge_notes], "recommendations": ["Seek urgent care."]},
            "rag_data": {"source": "hybrid", "summary": [{"title": "Chest Pain Evaluation", "source": "guideline.md", "excerpt": huge_notes}]},
        },
        {
            "understanding": huge_notes,
            "clinical_interpretation": huge_notes,
            "possible_causes": ["cardiovascular strain"],
            "follow_up_questions": ["When did it start?"],
            "recommendations": ["Seek urgent care."],
            "risk_level": "HIGH",
            "message": huge_notes,
        },
    )

    assert len(prompt) < 12000
    assert "Chest Pain Evaluation" in prompt
    assert "very long note " * 50 not in prompt
