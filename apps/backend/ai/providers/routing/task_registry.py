from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ..tasks.catalog import TASK_MODEL_MAP


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class TaskRoutingPolicy:
    task: str
    workflow: str
    primary_model: str
    fallback_models: list[str] = field(default_factory=list)
    primary_provider: str = "nvidia"
    fallback_providers: list[str] = field(default_factory=lambda: ["ollama"])
    latency_budget_seconds: float = 10.0
    require_structured_output: bool = True
    prefer_streaming: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def _provider_model(profile: str, provider: str) -> str:
    profile = (profile or "default").strip().lower()
    provider = (provider or "nvidia").strip().lower()
    if provider == "nvidia":
        env_map = {
            "fast": "NVIDIA_FAST_MODEL",
            "reasoning": "NVIDIA_REASONING_MODEL",
            "summary": "NVIDIA_SUMMARY_MODEL",
            "chat": "NVIDIA_CHAT_MODEL",
            "ocr": "NVIDIA_OCR_ANALYSIS_MODEL",
            "structured": "NVIDIA_STRUCTURED_JSON_MODEL",
        }
        env_name = env_map.get(profile, "NVIDIA_DEFAULT_MODEL")
        default_model = "meta/llama-3.1-8b-instruct" if profile == "fast" else os.getenv("NVIDIA_DEFAULT_MODEL", "meta/llama-3.1-70b-instruct")
        resolved = os.getenv(env_name, default_model).strip()
        if profile == "fast" and "70b" in resolved.lower():
            return "meta/llama-3.1-8b-instruct"
        return resolved
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip()
    if provider == "openai":
        return os.getenv("RAG_LLM_MODEL", "gpt-4o-mini").strip()
    return "unknown"


def build_task_policy(task: str, workflow: str | None = None) -> TaskRoutingPolicy:
    entry = TASK_MODEL_MAP.get(task, {})
    model_profile = str(entry.get("model_profile") or "fast")
    workflow_name = str(workflow or entry.get("workflow") or "generic")
    primary_provider = str(entry.get("primary_provider") or os.getenv("AI_PROVIDER_PRIMARY", "nvidia")).strip().lower()
    fallback_providers = [
        item.strip().lower()
        for item in str(os.getenv("AI_PROVIDER_FALLBACK_CHAIN", "nvidia,ollama,openai")).split(",")
        if item.strip()
    ]
    fallback_providers = [item for item in fallback_providers if item != primary_provider]
    primary_model = _provider_model(model_profile, primary_provider)
    nvidia_fast = _provider_model("fast", "nvidia")
    ollama_model = _provider_model(model_profile, "ollama")
    fallback_models = [item for item in [nvidia_fast, ollama_model] if item and item != primary_model]
    return TaskRoutingPolicy(
        task=task,
        workflow=workflow_name,
        primary_model=primary_model,
        fallback_models=fallback_models,
        primary_provider=primary_provider,
        fallback_providers=fallback_providers or ["ollama"],
        latency_budget_seconds=_env_float("AI_PROVIDER_DEFAULT_TIMEOUT_SECONDS", 12.0),
        require_structured_output=True,
        prefer_streaming=task in {"chat_assistant", "recommendations"},
        metadata={"model_profile": model_profile},
    )
