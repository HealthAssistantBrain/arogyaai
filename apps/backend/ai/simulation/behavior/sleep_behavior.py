from __future__ import annotations


class SleepBehavior:
    @staticmethod
    def nightly_target_hours(profile: dict, sleep_debt: float, stress_load: float) -> float:
        baseline = float(profile["baseline_metrics"]["sleep_hours"])
        discipline = float(profile["behavior_traits"]["sleep_discipline"])
        recovery_bias = (1.0 - stress_load) * 0.4 + (sleep_debt * 0.3)
        return max(4.5, min(9.5, baseline + discipline * 0.6 + recovery_bias - stress_load * 0.8))
