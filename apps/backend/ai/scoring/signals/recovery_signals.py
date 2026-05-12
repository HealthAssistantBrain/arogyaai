from __future__ import annotations

from typing import Any

from ..models.baseline_profile import BaselineProfile


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class RecoverySignalBuilder:
    @staticmethod
    def build(current: dict[str, Any], baseline: BaselineProfile) -> dict[str, float | None]:
        resting_hr = _safe_float(current.get("resting_hr"))
        hrv = _safe_float(current.get("hrv"))
        sleep_hours = _safe_float(current.get("sleep_hours"))
        activity_steps = _safe_float(current.get("activity_steps"))
        stress_level = _safe_float(current.get("stress_level"))

        baseline_rhr = baseline.reference_value("resting_hr", 60.0) or 60.0
        baseline_hrv = baseline.reference_value("hrv", 48.0) or 48.0
        baseline_sleep = baseline.reference_value("sleep_hours", 7.2) or 7.2
        baseline_steps = baseline.reference_value("activity_steps", 7000.0) or 7000.0

        sleep_component = 100.0 - max(0.0, abs((sleep_hours or baseline_sleep) - baseline_sleep) * 15.0)
        hrv_component = 100.0 - max(0.0, baseline_hrv - (hrv or baseline_hrv)) * 1.5
        rhr_component = 100.0 - max(0.0, (resting_hr or baseline_rhr) - baseline_rhr) * 2.2
        load_penalty = 0.0
        if activity_steps is not None and activity_steps > baseline_steps * 1.35 and sleep_hours is not None and sleep_hours < baseline_sleep:
            load_penalty = min(18.0, (activity_steps - baseline_steps) / max(1.0, baseline_steps) * 35.0)
        stress_penalty = max(0.0, (stress_level or 4.0) - 5.0) * 3.0
        recovery_proxy = max(0.0, min(100.0, sleep_component * 0.35 + hrv_component * 0.3 + rhr_component * 0.25 + 12.0 - load_penalty - stress_penalty))
        return {
            "recovery_proxy": round(recovery_proxy, 3),
            "baseline_sleep_hours": baseline_sleep,
            "baseline_steps": baseline_steps,
            "baseline_resting_hr": baseline_rhr,
            "baseline_hrv": baseline_hrv,
        }
