from __future__ import annotations


class BurnoutRecovery:
    @staticmethod
    def apply(state: dict, adherence: float, sleep_target: float) -> None:
        relief = adherence * 0.03 + max(0.0, sleep_target - 7.0) * 0.015
        state["burnout_load"] = max(0.0, state["burnout_load"] * 0.96 - relief)
