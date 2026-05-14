from __future__ import annotations


class AdherenceBehavior:
    @staticmethod
    def daily_adherence(profile: dict, burnout_load: float, intervention_load: float) -> float:
        baseline = float(profile["behavior_traits"]["adherence"])
        adherence = baseline - burnout_load * 0.22 + intervention_load * 0.18
        return max(0.05, min(0.98, adherence))
