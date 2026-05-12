from __future__ import annotations

from ..schemas import NarrativeContext


class RecoveryMemory:
    def build(self, context: NarrativeContext) -> dict[str, list[str]]:
        return {
            "recovery_trends": list(context.longitudinal_summary.get("major_trends") or []),
        }
