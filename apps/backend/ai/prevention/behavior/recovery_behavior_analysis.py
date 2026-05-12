from __future__ import annotations

from ..utils import metric_value


class RecoveryBehaviorAnalysis:
    @staticmethod
    def analyze(context: dict, habits: dict, adherence: dict) -> dict:
        sleep_duration = metric_value(context, "sleep_duration", "sleep")
        stress_level = metric_value(context, "stress")
        steps_avg = metric_value(context, "steps_avg_7d", "activity_level")
        contributors: list[str] = []

        if sleep_duration is not None and sleep_duration < 7.0:
            contributors.append("Recent sleep duration is not yet fully supporting recovery stability.")
        if stress_level is not None and stress_level >= 6.0:
            contributors.append("Self-reported or inferred stress is likely delaying full recovery.")
        if steps_avg is not None and steps_avg < 5000.0:
            contributors.append("Lower recent activity may reflect reduced resilience or incomplete recovery.")
        if not contributors:
            contributors.append("Recovery behavior looks broadly supportive, but the pattern still needs continued observation.")

        return {
            "contributors": contributors[:4],
            "habits": habits,
            "adherence": adherence,
            "summary": contributors[0],
        }
