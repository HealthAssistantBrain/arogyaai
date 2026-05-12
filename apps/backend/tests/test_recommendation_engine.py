from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services import recommendation_engine
from services.recommendation_service import RecommendationSignals


def _stub_rag(condition, signals):
    return {
        "query": condition,
        "basis": "Clinical reference: prevention guidance supports objective monitoring and lifestyle steps.",
        "sources": [{"title": "Clinical reference", "source": "ArogyaAI"}],
    }


def test_cardio_plan_contains_actionable_sections(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"cardiovascular": 0.78},
            vitals={"steps": 3200, "systolic_bp": 146, "diastolic_bp": 94, "heart_rate": 112},
            drivers=[{"label": "Diastolic blood pressure", "domains": ["cardiovascular"]}],
            has_ml=True,
            has_vitals=True,
        )
    )

    plan = plans[0]
    assert plan["condition_key"] == "cardiovascular"
    assert plan["risk_level"] == "HIGH"
    assert plan["lifestyle"]["diet"]
    assert plan["clinical_actions"]["tests"]
    assert plan["action_plan"]["daily"]
    assert plan["monitoring"]["thresholds"]
    assert any("8,000 daily steps" in item["text"] for item in plan["lifestyle"]["activity"])
    assert all(item["priority"] in {"HIGH", "MEDIUM", "LOW"} for item in plan["precautions"])


def test_diabetes_plan_prioritizes_sugar_restriction_and_glucose_tests(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"diabetes": 0.71},
            labs=[{"name": "HbA1c", "value": 7.1, "unit": "%", "status": "high", "category": "glucose"}],
            vitals={"steps": 7600, "sleep_hours": 5.7},
            symptoms={"chief_complaint": "Frequent urination and fatigue"},
            has_ml=True,
            has_labs=True,
            has_vitals=True,
            has_symptoms=True,
        )
    )

    plan = plans[0]
    tests = [item["text"] for item in plan["clinical_actions"]["tests"]]
    precautions = [item["text"] for item in plan["precautions"]]

    assert plan["condition_key"] == "diabetes"
    assert any("sugary drinks" in item.lower() for item in precautions)
    assert any("HbA1c" in item for item in tests)
    assert any("Fasting glucose" in item or "post-meal glucose" in item for item in tests)
    assert any(item["priority"] == "HIGH" for item in plan["clinical_actions"]["tests"])


def test_low_steps_use_incremental_plan_below_5000(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"diabetes": 0.46},
            vitals={"steps": 4800},
            has_ml=True,
            has_vitals=True,
        )
    )

    activity_text = " ".join(item["text"] for item in plans[0]["lifestyle"]["activity"])
    daily_text = " ".join(item["text"] for item in plans[0]["action_plan"]["daily"])

    assert "Increase by 500 to 1,000 steps" in activity_text
    assert "Increase steps by 500 to 1,000" in daily_text


def test_bp_130_80_adds_sodium_and_daily_monitoring(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"sleep": 0.52},
            vitals={"systolic_bp": 130, "diastolic_bp": 80},
            has_ml=True,
            has_vitals=True,
        )
    )

    plan_text = " ".join(
        item["text"]
        for section in (
            plans[0]["precautions"],
            plans[0]["lifestyle"]["diet"],
            plans[0]["action_plan"]["daily"],
            plans[0]["monitoring"]["metrics"],
        )
        for item in section
    )

    assert "Limit sodium" in plan_text
    assert "Measure blood pressure daily" in plan_text
    assert "Blood pressure" in plan_text


def test_heart_rate_below_50_adds_caution_and_clinician_review(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"cardiovascular": 0.42},
            vitals={"heart_rate": 48},
            has_ml=True,
            has_vitals=True,
        )
    )

    plan = plans[0]
    precautions = [item["text"] for item in plan["precautions"]]
    thresholds = [item["text"] for item in plan["monitoring"]["thresholds"]]

    assert any("may need caution" in item for item in precautions)
    assert "heart rate below 50" in plan["clinical_actions"]["doctor_visit"]["text"].lower()
    assert any("below 50" in item for item in thresholds)


def test_fasting_glucose_100_adds_sugar_control_and_tests(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _stub_rag)

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"sleep": 0.5},
            labs=[{"name": "Fasting glucose", "value": 108, "unit": "mg/dL", "status": "normal"}],
            has_ml=True,
            has_labs=True,
        )
    )

    plan = plans[0]
    plan_text = " ".join(
        item["text"]
        for section in (
            plan["precautions"],
            plan["lifestyle"]["diet"],
            plan["clinical_actions"]["tests"],
            plan["monitoring"]["thresholds"],
        )
        for item in section
    )

    assert "Avoid sugary drinks" in plan_text
    assert "HbA1c and repeat fasting glucose" in plan_text
    assert "100 to 125 may indicate elevated risk" in plan_text


def test_all_predicted_conditions_generate_one_plan_each_when_low_risk(monkeypatch):
    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", lambda condition, signals: {"query": condition, "basis": "", "sources": [], "rag_status": "fallback"})

    plans = recommendation_engine.build_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={
                "cardiovascular": 0.22,
                "diabetes": 0.18,
                "respiratory": 0.12,
            },
            has_ml=True,
        )
    )

    assert [plan["condition_key"] for plan in plans] == ["cardiovascular", "diabetes", "respiratory"]
    assert len(plans) == 3
    assert all(plan["risk_level"] == "LOW" for plan in plans)
    assert all(plan["badge_label"] == "Preventive Care" for plan in plans)
    assert all("No immediate concern" in plan["summary"] for plan in plans)
    assert all(plan["fallback_recommendation"]["summary"] for plan in plans)


def test_fast_recommendation_plans_do_not_call_rag(monkeypatch):
    def _fail_rag(_condition, _signals):
        raise AssertionError("fast path must not retrieve RAG context")

    monkeypatch.setattr(recommendation_engine, "_retrieve_rag_context", _fail_rag)

    plans = recommendation_engine.build_fast_recommendation_plans(
        RecommendationSignals(
            disease_probabilities={"cardiovascular": 0.78},
            vitals={"steps": 3200, "systolic_bp": 146, "diastolic_bp": 94},
            has_ml=True,
            has_vitals=True,
        )
    )

    assert plans[0]["condition_key"] == "cardiovascular"
    assert plans[0]["snapshot_mode"] == "fast"
    assert plans[0]["rag_status"] == "deferred"
