from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.safety.confidence_scoring import compute_confidence
from ai.safety.safety_types import ConfidenceReport, ContradictionReport, ConversationContext, HallucinationReport, ProviderType


def test_confidence_stays_reasonable_with_grounded_context():
    context = ConversationContext(
        user_id="user-1",
        session_id="session-1",
        user_symptoms=["headache", "high blood pressure"],
        vitals={"systolic_bp": 148, "diastolic_bp": 92},
        ml_predictions={"hypertension": {"probability": 0.72}},
        rag_evidence=[{"content": "Hypertension management includes lifestyle modifications."}],
        rag_confidence=0.88,
        provider=ProviderType.NVIDIA,
        raw_model_confidence=0.84,
    )
    report = compute_confidence(
        context,
        HallucinationReport(False, [], [], 0.88, "none"),
        ContradictionReport(False, [], "none"),
    )
    assert report.score >= 0.6
    assert "High confidence" in report.reason or "Moderate confidence" in report.reason
