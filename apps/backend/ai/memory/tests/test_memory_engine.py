from __future__ import annotations

from datetime import datetime, timezone

from ..emotional_memory import _detect_tone
from ..episodic_memory import _detect_follow_up_needed, _extract_recommendations, _extract_symptoms
from ..health_memory import _compute_trend
from ..memory_decay import compute_decay_score
from ..memory_ranker import score_importance_from_text
from ..memory_types import EmotionalTone, MemoryImportance, MemoryItem, MemoryType, RetrievedMemoryContext


def test_ranker_trivial_greeting():
    result = score_importance_from_text("Hi how are you", symptoms=[], has_recommendations=False)
    assert result in {MemoryImportance.TRIVIAL, MemoryImportance.LOW}


def test_ranker_emergency_cardiac():
    result = score_importance_from_text(
        "severe chest pain and I can't breathe",
        symptoms=["chest pain"],
    )
    assert result == MemoryImportance.CRITICAL


def test_ranker_emotional_intensity_boosts_importance():
    result = score_importance_from_text("I've been feeling a bit off lately", emotional_intensity=0.8)
    assert result == MemoryImportance.HIGH


def test_decay_critical_memory_slow():
    score = compute_decay_score(MemoryImportance.CRITICAL, days_since_creation=90)
    assert score > 0.6


def test_decay_trivial_memory_fast():
    score = compute_decay_score(MemoryImportance.TRIVIAL, days_since_creation=3)
    assert score < 0.2


def test_decay_access_boost():
    no_access = compute_decay_score(MemoryImportance.MEDIUM, days_since_creation=20)
    with_access = compute_decay_score(MemoryImportance.MEDIUM, days_since_creation=20, access_count=5)
    assert with_access > no_access


def test_symptom_extraction():
    symptoms = _extract_symptoms("I have been experiencing chest pain and dizziness all morning")
    assert "chest pain" in symptoms
    assert "dizziness" in symptoms


def test_follow_up_detection():
    assert _detect_follow_up_needed("Please follow up with your doctor this week") is True
    assert _detect_follow_up_needed("You seem to be doing well today") is False


def test_recommendation_extraction():
    text = "I'd recommend you monitor your blood pressure daily. You should drink more water."
    recs = _extract_recommendations(text)
    assert recs
    assert any("blood pressure" in item.lower() or "water" in item.lower() for item in recs)


def test_detect_anxiety_tone():
    tone, intensity = _detect_tone("I'm really scared this might be something serious")
    assert tone == EmotionalTone.ANXIOUS
    assert intensity > 0.2


def test_detect_neutral_tone():
    tone, intensity = _detect_tone("What does eGFR mean?")
    assert tone == EmotionalTone.NEUTRAL or intensity < 0.3


def test_trend_improving_lower_is_better():
    trend, _ = _compute_trend("systolic_bp", current_value=130, prior_value=160)
    assert trend == "improving"


def test_trend_worsening_lower_is_better():
    trend, _ = _compute_trend("glucose", current_value=220, prior_value=140)
    assert trend == "worsening"


def test_trend_stable_within_threshold():
    trend, _ = _compute_trend("heart_rate", current_value=73, prior_value=75)
    assert trend == "stable"


def test_token_budget_prompt_generation():
    context = RetrievedMemoryContext(
        summaries=[
            MemoryItem(
                user_id="test",
                memory_type=MemoryType.SUMMARY,
                importance=MemoryImportance.HIGH,
                content="x" * 5000,
                created_at=datetime.now(timezone.utc),
            )
        ]
    )
    prompt = context.to_prompt_string()
    assert len(prompt) < 10000
