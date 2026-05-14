from __future__ import annotations


class IllnessRecovery:
    @staticmethod
    def apply(state: dict, adherence: float) -> None:
        state["illness_burden"] = max(0.0, state["illness_burden"] * (0.92 - adherence * 0.03))
