from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models.baseline_profile import BaselineProfile


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _severity_from_zscore(z_score: float) -> str:
    absolute = abs(z_score)
    if absolute >= 3.0:
        return "high"
    if absolute >= 2.0:
        return "moderate"
    return "low"


class AnomalyDetector:
    @staticmethod
    def detect(
        *,
        current: dict[str, Any],
        histories: dict[str, list[float]],
        baseline: BaselineProfile,
        timestamps: dict[str, datetime | None] | None = None,
    ) -> list[dict[str, Any]]:
        timestamps = timestamps or {}
        anomalies: list[dict[str, Any]] = []

        def register(metric: str, anomaly_type: str, value: float, baseline_value: float, z_score: float, message: str) -> None:
            anomalies.append(
                {
                    "type": anomaly_type,
                    "severity": _severity_from_zscore(z_score),
                    "metric": metric,
                    "message": message,
                    "value": round(value, 2),
                    "baseline": round(baseline_value, 2),
                    "z_score": round(z_score, 3),
                    "timestamp": timestamps.get(metric).isoformat() if timestamps.get(metric) else None,
                    "metadata": {"delta": round(value - baseline_value, 2)},
                }
            )

        hr = _safe_float(current.get("heart_rate"))
        hr_baseline = baseline.reference_value("heart_rate")
        hr_std = baseline.std_dev("heart_rate", 6.0) or 6.0
        if hr is not None and hr_baseline is not None and hr_std > 0:
            z_score = (hr - hr_baseline) / hr_std
            if z_score >= 2.0:
                register("heart_rate", "hr_spike", hr, hr_baseline, z_score, "Heart rate is materially above your recent baseline.")

        spo2 = _safe_float(current.get("spo2"))
        spo2_baseline = baseline.reference_value("spo2")
        spo2_std = baseline.std_dev("spo2", 1.0) or 1.0
        if spo2 is not None and spo2_baseline is not None and spo2_std > 0:
            z_score = (spo2 - spo2_baseline) / spo2_std
            if z_score <= -2.0 or spo2 < 94.0:
                register("spo2", "oxygen_drop", spo2, spo2_baseline, z_score, "Oxygen saturation has dropped below your typical range.")

        sleep = _safe_float(current.get("sleep_hours"))
        sleep_baseline = baseline.reference_value("sleep_hours")
        sleep_std = baseline.std_dev("sleep_hours", 0.8) or 0.8
        if sleep is not None and sleep_baseline is not None and sleep_std > 0:
            z_score = (sleep - sleep_baseline) / sleep_std
            if z_score <= -1.8:
                register("sleep_hours", "sleep_degradation", sleep, sleep_baseline, z_score, "Sleep duration is meaningfully below your baseline.")

        recovery = _safe_float(current.get("recovery_proxy"))
        recovery_baseline = baseline.reference_value("recovery_proxy")
        recovery_std = baseline.std_dev("recovery_proxy", 8.0) or 8.0
        if recovery is not None and recovery_baseline is not None and recovery_std > 0:
            z_score = (recovery - recovery_baseline) / recovery_std
            if z_score <= -1.8:
                register("recovery_proxy", "abnormal_recovery", recovery, recovery_baseline, z_score, "Recovery is below your normal range.")

        systolic_history = [float(value) for value in histories.get("blood_pressure_systolic", []) if value is not None]
        diastolic_history = [float(value) for value in histories.get("blood_pressure_diastolic", []) if value is not None]
        if len(systolic_history) >= 4 and len(diastolic_history) >= 4:
            sys_range = max(systolic_history[-4:]) - min(systolic_history[-4:])
            dia_range = max(diastolic_history[-4:]) - min(diastolic_history[-4:])
            if sys_range >= 18.0 or dia_range >= 12.0:
                anomalies.append(
                    {
                        "type": "bp_instability",
                        "severity": "moderate" if sys_range < 25.0 else "high",
                        "metric": "blood_pressure",
                        "message": "Blood pressure has become unstable across recent readings.",
                        "value": round(sys_range + dia_range, 2),
                        "baseline": 0.0,
                        "z_score": round(max(sys_range / 18.0, dia_range / 12.0), 3),
                        "timestamp": None,
                        "metadata": {
                            "systolic_range": round(sys_range, 2),
                            "diastolic_range": round(dia_range, 2),
                        },
                    }
                )

        fatigue_series = [float(value) for value in histories.get("fatigue_proxy", []) if value is not None]
        if len(fatigue_series) >= 3 and fatigue_series[-1] - fatigue_series[0] >= 10.0:
            anomalies.append(
                {
                    "type": "fatigue_trend",
                    "severity": "moderate",
                    "metric": "fatigue_proxy",
                    "message": "Fatigue pressure has been building across recent observations.",
                    "value": round(fatigue_series[-1], 2),
                    "baseline": round(fatigue_series[0], 2),
                    "z_score": round((fatigue_series[-1] - fatigue_series[0]) / 10.0, 3),
                    "timestamp": None,
                    "metadata": {},
                }
            )

        return anomalies
