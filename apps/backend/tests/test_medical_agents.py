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

from services.agents import (
    MLRiskInterpretationAgent,
    RAGKnowledgeAgent,
    SymptomAnalysisAgent,
    run_medical_pipeline,
)
from services.agents.rag_agent import _RAG_CACHE


def _sample_ml_data() -> dict:
    return {
        "prediction_id": "pred-1",
        "overall_risk": 0.86,
        "risk_level": "LOW",
        "condition_risks": {"cardiovascular": 0.86, "diabetes": 0.24},
        "possible_conditions": ["Cardiovascular disease risk"],
        "shap_drivers": [
            {"feature_name": "heart_rate", "label": "Heart Rate", "impact": 0.3, "direction": "increase"},
            {"feature_name": "blood_pressure", "label": "Blood Pressure", "impact": 0.2, "direction": "increase"},
        ],
        "recommendations": [{"detail": "Recheck resting heart rate after hydration and rest."}],
    }


def _sample_user_context() -> dict:
    return {
        "vitals": {
            "heart_rate": {"latest": 122, "unit": "bpm"},
            "blood_pressure_systolic": {"latest": 148, "unit": "mmHg"},
        },
        "lab_results": [{"name": "Glucose", "value": 132, "unit": "mg/dL", "status": "high"}],
        "abnormal_labs": [{"name": "Glucose", "value": 132, "unit": "mg/dL", "status": "high"}],
        "clinical_history": {"analysis": {"symptoms": ["dizziness"]}},
    }


async def _fake_retrieve(query: str, **_kwargs) -> dict:
    return {
        "query": query,
        "source": "test",
        "summary": [
            {
                "title": "Chest Pain Evaluation",
                "source": "test-guideline.md",
                "category": "cardiovascular",
                "excerpt": "Chest pain with dizziness can need urgent assessment.",
                "score": 0.91,
            }
        ],
        "documents": [],
    }


def test_symptom_agent_returns_structured_symptoms_severity_and_categories():
    result = SymptomAnalysisAgent().run("I have chest pain and dizziness, about 8/10.")

    assert "chest pain" in result["symptom_names"]
    assert "dizziness" in result["symptom_names"]
    assert result["severity"] == "high"
    assert "cardiovascular" in result["possible_categories"]
    assert result["structured_symptoms"][0]["name"]


def test_ml_agent_interprets_high_numeric_risk_even_if_label_is_low():
    result = MLRiskInterpretationAgent().run(_sample_ml_data())

    assert result["risk_level"] == "HIGH"
    assert result["available"] is True
    assert result["top_drivers"][0]["label"] == "Heart Rate"
    assert "higher-concern" in result["interpretation"]


def test_rag_agent_caches_retrieval_results():
    _RAG_CACHE.clear()
    calls = {"count": 0}

    async def counted_retrieve(query: str, **kwargs) -> dict:
        calls["count"] += 1
        return await _fake_retrieve(query, **kwargs)

    agent = RAGKnowledgeAgent()
    symptoms = {"symptom_names": ["chest pain"], "possible_categories": ["cardiovascular"]}
    first = asyncio.run(agent.run("I have chest pain", symptoms, retrieve_fn=counted_retrieve))
    second = asyncio.run(agent.run("I have chest pain", symptoms, retrieve_fn=counted_retrieve))

    assert calls["count"] == 1
    assert first["summary"][0]["title"] == "Chest Pain Evaluation"
    assert second["cache_hit"] is True


def test_full_medical_pipeline_runs_and_triggers_safety_guard():
    result = asyncio.run(
        run_medical_pipeline(
            "user-1",
            "I have chest pain and dizziness",
            ml_data=_sample_ml_data(),
            user_context=_sample_user_context(),
            retrieve_rag=_fake_retrieve,
            conversation_history=[],
        )
    )

    final_response = result["final_response"]
    assert result["success"] is True
    assert result["symptom_analysis"]["symptom_names"]
    assert result["ml_interpretation"]["risk_level"] == "HIGH"
    assert result["rag_data"]["summary"]
    assert result["clinical_reasoning"]["clinical_interpretation"]
    assert result["safety"]["requires_immediate_care"] is True
    assert final_response["message"]
    assert final_response["risk_level"] == "HIGH"
    assert final_response["reasoning"]["clinical_interpretation"]
    assert "Seek immediate medical care" in " ".join(final_response["safety_notes"])


def test_pipeline_continues_when_rag_agent_fails():
    async def failing_retrieve(_query: str, **_kwargs) -> dict:
        raise RuntimeError("retriever unavailable")

    result = asyncio.run(
        run_medical_pipeline(
            "user-1",
            "Why is my heart rate high?",
            ml_data=_sample_ml_data(),
            user_context=_sample_user_context(),
            retrieve_rag=failing_retrieve,
        )
    )

    assert result["success"] is True
    assert result["rag_data"]["summary"]
    assert result["rag_data"]["source"] == "minimal_medical_context"
    assert result["final_response"]["message"]
    assert any(item["agent"] == "rag_knowledge_agent" and item["status"] == "completed" for item in result["agent_trace"])
    assert any(item["name"] == "rag_knowledge_agent" and item["status"] == "completed" for item in result["reasoning_steps"])


def test_pipeline_uses_baseline_ml_when_prediction_is_unavailable():
    result = asyncio.run(
        run_medical_pipeline(
            "user-1",
            "Why is my heart rate high?",
            user_context=_sample_user_context(),
            retrieve_rag=_fake_retrieve,
        )
    )

    ml_data = result["raw_context"]["ml_data"]
    assert ml_data["source"] == "baseline_logic"
    assert ml_data["overall_risk"] is not None
    assert ml_data["shap_drivers"]
    assert result["ml_interpretation"]["top_drivers"]
    assert result["final_response"]["contributing_factors"]
