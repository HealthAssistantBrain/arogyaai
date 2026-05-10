from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.safety.contradiction_checker import check_contradictions
from ai.safety.safety_types import ConversationContext


def test_reassuring_language_conflicts_with_critical_vitals():
    report = check_contradictions(
        "Your cardiovascular health looks generally fine.",
        ConversationContext(
            user_id="user-1",
            session_id="session-1",
            vitals={"systolic_bp": 188, "heart_rate": 118},
            ml_predictions={"cvd": {"probability": 0.81}},
        ),
    )
    assert report.detected is True
    assert report.severity == "critical"
    assert len(report.contradictions) >= 2
