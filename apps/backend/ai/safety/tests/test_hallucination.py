from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.safety.hallucination_detector import detect_hallucinations
from ai.safety.safety_types import ConversationContext


def test_fabricated_statistics_are_flagged():
    context = ConversationContext(
        user_id="user-1",
        session_id="session-1",
        rag_evidence=[{"content": "General kidney disease information without exact percentages."}],
        rag_confidence=0.4,
    )
    report = detect_hallucinations(
        "Based on your profile, there's a 67.3% chance of kidney disease and 84% of patients like you develop CKD.",
        context,
    )
    assert report.detected is True
    assert report.severity == "severe"
    assert report.fabricated_claims
