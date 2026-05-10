from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.formatters import ResponseFormatter


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        request_id="req-123",
        raw_response={
            "text": "```json\n{\"message\": \"You may be experiencing a watchful symptom pattern.\", \"possible_causes\": [\"dehydration\", \"viral illness\"], \"recommendations\": [\"Hydrate well.\", \"Recheck temperature tonight.\"], \"risk_level\": \"medium\"}\n```"
        },
        provider_metadata={"provider": "nvidia", "model": "clinical-v1"},
        retrieved_knowledge={
            "source": "hybrid",
            "cache_hit": True,
            "summary": [
                {"title": "Fever in Adults", "source": "fever.md", "similarity": 0.82},
                {"title": "Hydration Advice", "source": "hydration.md", "similarity": 0.75},
            ],
        },
        user_context={
            "vitals": {"heart_rate": {"latest": 96}},
            "lab_results": [{"name": "CRP", "value": 8.0}],
            "wearable_trends": {"sleep": {"avg_7d": 6.4}},
            "clinical_history": {"summary": "Recent febrile illness"},
        },
        memory={"wearable_context": {"sleep": {"avg_7d": 6.4}}},
        stage_timings_ms={"provider_inference": 122.4, "structured_formatting": 8.2},
    )


def test_formatter_normalizes_markdown_and_builds_render_contract():
    formatter = ResponseFormatter()

    payload = formatter.format_payload(
        workflow="chatbot",
        payload={"provider": "nvidia"},
        context=_context(),
        response_status="ready",
    )

    assert payload["summary"]
    assert payload["structured_sections"]
    assert payload["structured_sections"][0]["title"] == "Direct Answer"
    assert payload["citations"][0]["title"] == "Fever in Adults"
    assert payload["rendering"]["confidence_badge"]["label"] in {"Moderate", "High", "Guarded"}
    assert payload["streaming"]["progressive_hydration"] is True
    assert "markdown_cleanup" in payload["formatter_diagnostics"]["repairs_applied"]
    assert payload["cache_hit"] is True


def test_formatter_downgrades_dangerous_or_overcertain_medical_language():
    formatter = ResponseFormatter()
    context = _context()
    context.raw_response = {
        "text": "{\"message\": \"You definitely have pneumonia and should stop all medication.\", \"recommendations\": [\"Ignore the symptoms if you feel better tomorrow.\"], \"risk_level\": \"low\"}"
    }

    payload = formatter.format_payload(
        workflow="chatbot",
        payload={"provider": "openai"},
        context=context,
        response_status="ready",
    )

    warning_codes = {
        item.get("code")
        for item in payload["warnings"]
        if isinstance(item, dict)
    }
    assert "unsupported_certainty" in warning_codes
    assert "dangerous_medical_advice" in warning_codes
    assert payload["confidence_score"] < 0.65
    assert "supportive guidance" in payload["medical_disclaimer"].lower()


def test_formatter_shapes_disease_simulator_sections_without_dropping_legacy_fields():
    formatter = ResponseFormatter()

    payload = formatter.format_payload(
        workflow="disease_simulator",
        payload={
            "summary": "If the user sustains the simulated changes, cardiovascular risk may improve.",
            "focus_summary": "Cardiovascular risk falls in the simulated scenario.",
            "current_risk": {"cardiovascular": 0.72, "diabetes": 0.41},
            "simulated_risk": {"cardiovascular": 0.43, "diabetes": 0.29},
            "delta": {"cardiovascular": -0.29, "diabetes": -0.12},
            "recommendations": [{"title": "Walk daily", "detail": "Maintain 8k-10k steps."}],
            "key_drivers": [{"label": "Steps", "impact": "-0.19", "detail": "Higher step count improves risk."}],
            "provider": "hybrid_ml_plus_rules",
        },
        response_status="ready",
        provider="hybrid_ml_plus_rules",
        model="rf-v1",
        raw_response={"simulated_risk": {"cardiovascular": 0.43}},
    )

    assert payload["current_risk"]["cardiovascular"] == 0.72
    assert payload["structured_sections"][0]["title"] == "Scenario Overview"
    assert payload["rendering"]["charts"][0]["id"] == "risk-comparison"
    assert payload["rendering"]["recommendations"][0]["title"] == "Walk daily"
