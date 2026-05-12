from __future__ import annotations

from ..utils import clamp, metric_value


class HabitTracking:
    @staticmethod
    def build(context: dict) -> dict:
        steps_avg = metric_value(context, "steps_avg_7d", "activity_level")
        sleep_efficiency = metric_value(context, "sleep_efficiency", "sleep_score")
        sleep_duration = metric_value(context, "sleep_duration", "sleep")
        stress_level = metric_value(context, "stress")

        sleep_consistency = clamp((sleep_efficiency or 72.0), 0.0, 100.0)
        activity_consistency = clamp(((steps_avg or 6500.0) / 100.0), 0.0, 100.0)
        recovery_routine = clamp(
            100.0
            - max(0.0, 7.0 - (sleep_duration or 7.0)) * 10.0
            - max(0.0, (stress_level or 4.0) - 4.0) * 8.0,
            0.0,
            100.0,
        )
        drift_score = clamp(100.0 - ((sleep_consistency * 0.4) + (activity_consistency * 0.35) + (recovery_routine * 0.25)))
        return {
            "sleep_consistency": round(sleep_consistency, 4),
            "activity_consistency": round(activity_consistency, 4),
            "recovery_routine": round(recovery_routine, 4),
            "drift_score": round(drift_score, 4),
            "summary": (
                "Behavioral drift is making recovery less reliable."
                if drift_score >= 55.0
                else "Daily habits are providing a reasonable preventive base."
            ),
        }
