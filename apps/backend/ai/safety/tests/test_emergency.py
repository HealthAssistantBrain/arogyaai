from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.safety.emergency_escalation import scan_for_emergency
from ai.safety.safety_types import ConversationContext


def test_self_harm_has_highest_priority():
    report = scan_for_emergency(
        "I want to hurt myself and I also have chest pain",
        "Please stay calm.",
        ConversationContext(user_id="user-1", session_id="session-1"),
    )
    assert report.is_emergency is True
    assert report.tier == "self_harm"
    assert "iCall" in (report.override_response or "")
