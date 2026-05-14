from __future__ import annotations

from typing import Any

from .._shared import safe_mean


class TrajectorySimulator:
    @staticmethod
    def summarize(points: list[dict[str, Any]]) -> dict[str, Any]:
        phases = {"stable": 0, "recovery": 0, "deterioration": 0}
        for point in points:
            phases[point["trajectory_phase"]] = phases.get(point["trajectory_phase"], 0) + 1
        fatigue = [point["state"]["fatigue_load"] for point in points]
        recovery = [point["recovery_index"] for point in points if point.get("recovery_index") is not None]
        return {
            "dominant_phase": max(phases, key=phases.get) if phases else "stable",
            "phase_counts": phases,
            "fatigue_trend": round((fatigue[-1] - fatigue[0]) if len(fatigue) > 1 else 0.0, 4),
            "mean_recovery_index": round(safe_mean(recovery), 2),
        }
