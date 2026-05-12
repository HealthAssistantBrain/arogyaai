from __future__ import annotations

from typing import Any

from ..schemas import MetricSignal, NarrativeContext, unique_texts

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}

_METRIC_SPECS: dict[str, dict[str, Any]] = {
    "sleep_duration": {
        "label": "Sleep duration",
        "unit": "h",
        "aliases": ("sleep_duration", "sleep", "sleep_hours"),
        "baseline_aliases": ("sleep_duration_baseline", "sleep_avg_7d", "sleep_7d_avg"),
        "vital_keys": ("sleep",),
        "lower_is_better": False,
    },
    "resting_hr": {
        "label": "Resting heart rate",
        "unit": " bpm",
        "aliases": ("resting_hr", "avg_rhr", "heart_rate", "hr_mean_7d"),
        "baseline_aliases": ("resting_hr_baseline", "avg_rhr_baseline", "rhr_baseline"),
        "vital_keys": ("heart_rate", "resting_hr"),
        "lower_is_better": True,
    },
    "hrv": {
        "label": "HRV",
        "unit": " ms",
        "aliases": ("hrv", "overnight_hrv", "hrv_score"),
        "baseline_aliases": ("hrv_baseline", "hrv_avg_7d"),
        "vital_keys": ("hrv",),
        "lower_is_better": False,
    },
    "recovery_score": {
        "label": "Recovery",
        "unit": "",
        "aliases": ("recovery_score", "recovery", "recovery_index"),
        "baseline_aliases": ("recovery_baseline", "recovery_score_baseline"),
        "vital_keys": ("recovery",),
        "lower_is_better": False,
    },
    "stress_score": {
        "label": "Stress",
        "unit": "",
        "aliases": ("stress_score", "stress", "stress_index"),
        "baseline_aliases": ("stress_baseline", "stress_score_baseline"),
        "vital_keys": ("stress",),
        "lower_is_better": True,
    },
    "activity_steps": {
        "label": "Activity",
        "unit": " steps",
        "aliases": ("activity_level", "steps", "steps_avg_7d"),
        "baseline_aliases": ("activity_level_baseline", "steps_baseline", "steps_7d_avg"),
        "vital_keys": ("steps", "activity"),
        "lower_is_better": False,
    },
    "glucose": {
        "label": "Glucose",
        "unit": " mg/dL",
        "aliases": ("glucose", "fasting_glucose"),
        "baseline_aliases": ("glucose_baseline", "glucose_avg_7d"),
        "vital_keys": ("glucose",),
        "lower_is_better": True,
    },
    "hba1c": {
        "label": "HbA1c",
        "unit": "%",
        "aliases": ("hba1c", "a1c"),
        "baseline_aliases": ("hba1c_baseline",),
        "vital_keys": ("hba1c", "a1c"),
        "lower_is_better": True,
    },
    "spo2": {
        "label": "SpO2",
        "unit": "%",
        "aliases": ("spo2", "oxygen_saturation"),
        "baseline_aliases": ("spo2_baseline",),
        "vital_keys": ("spo2", "oxygen_saturation"),
        "lower_is_better": False,
    },
    "respiratory_rate": {
        "label": "Respiratory rate",
        "unit": " rpm",
        "aliases": ("resp_rate", "respiratory_rate"),
        "baseline_aliases": ("resp_rate_baseline", "respiratory_rate_baseline"),
        "vital_keys": ("resp_rate", "respiratory_rate"),
        "lower_is_better": True,
    },
    "systolic_bp": {
        "label": "Systolic blood pressure",
        "unit": " mmHg",
        "aliases": ("systolic_bp",),
        "baseline_aliases": ("systolic_bp_baseline",),
        "vital_keys": ("systolic_bp", "blood_pressure"),
        "lower_is_better": True,
    },
    "diastolic_bp": {
        "label": "Diastolic blood pressure",
        "unit": " mmHg",
        "aliases": ("diastolic_bp",),
        "baseline_aliases": ("diastolic_bp_baseline",),
        "vital_keys": ("diastolic_bp", "blood_pressure"),
        "lower_is_better": True,
    },
    "bmi": {
        "label": "BMI",
        "unit": "",
        "aliases": ("bmi",),
        "baseline_aliases": ("bmi_baseline",),
        "vital_keys": ("bmi",),
        "lower_is_better": True,
    },
    "fatigue_score": {
        "label": "Fatigue",
        "unit": "",
        "aliases": ("fatigue_score", "fatigue"),
        "baseline_aliases": ("fatigue_baseline",),
        "vital_keys": ("fatigue",),
        "lower_is_better": True,
    },
    "air_quality": {
        "label": "Air quality",
        "unit": " AQI",
        "aliases": ("air_quality", "aqi"),
        "baseline_aliases": ("air_quality_baseline",),
        "vital_keys": ("aqi", "air_quality"),
        "lower_is_better": True,
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_float(container: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if "." in key:
            parent, child = key.split(".", 1)
            nested = container.get(parent)
            if isinstance(nested, dict):
                numeric = _safe_float(nested.get(child))
                if numeric is not None:
                    return numeric
            continue
        numeric = _safe_float(container.get(key))
        if numeric is not None:
            return numeric
    return None


def _metric_status(current: float | None, baseline: float | None, lower_is_better: bool) -> tuple[str, float | None, float | None]:
    if current is None or baseline in (None, 0):
        return ("stable", None, None if baseline is None else current - baseline if current is not None else None)
    delta = current - baseline
    delta_pct = abs(delta) / max(abs(baseline), 1e-6)
    if delta_pct < 0.06:
        return ("stable", round(delta_pct, 4), round(delta, 4))
    worsened = delta > 0 if lower_is_better else delta < 0
    improved = delta < 0 if lower_is_better else delta > 0
    if worsened:
        return ("elevated" if lower_is_better else "reduced", round(delta_pct, 4), round(delta, 4))
    if improved:
        return ("improving", round(delta_pct, 4), round(delta, 4))
    return ("stable", round(delta_pct, 4), round(delta, 4))


def _normalize_risk_scores(risk_payload: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in risk_payload.items():
        numeric = _safe_float(value)
        if numeric is None:
            continue
        if abs(numeric) > 1:
            numeric /= 100.0
        normalized[str(key)] = max(0.0, min(1.0, numeric))
    return normalized


class HealthContextBuilder:
    def build(
        self,
        *,
        workflow: str,
        user_id: str = "",
        source: str = "deterministic_reasoning",
        risk_payload: dict[str, Any] | None = None,
        feature_payload: dict[str, Any] | None = None,
        vitals: dict[str, Any] | None = None,
        wearable_trends: dict[str, Any] | None = None,
        forecasting: dict[str, Any] | None = None,
        clinical_history: dict[str, Any] | None = None,
        drivers: list[dict[str, Any]] | None = None,
        shap_values: list[dict[str, Any]] | None = None,
        anomalies: list[dict[str, Any]] | None = None,
        recommendations: list[Any] | None = None,
        recommendation_plans: list[dict[str, Any]] | None = None,
        labs: list[dict[str, Any]] | None = None,
        ocr_summary: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        disease_simulation: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> NarrativeContext:
        risk_payload = dict(risk_payload or {})
        feature_payload = dict(feature_payload or {})
        vitals = dict(vitals or {})
        wearable_trends = dict(wearable_trends or {})
        forecasting = dict(forecasting or {})
        clinical_history = dict(clinical_history or {})
        user_context = dict(user_context or {})
        extra = dict(extra or {})

        risk_scores = _normalize_risk_scores(risk_payload.get("risk_scores") or risk_payload.get("risks") or risk_payload)
        risk_score = _safe_float(
            risk_payload.get("overall_risk_score")
            or risk_payload.get("risk_score")
            or risk_payload.get("overall")
        )
        if risk_score is not None and abs(risk_score) > 1:
            risk_score /= 100.0
        risk_score = max(0.0, min(1.0, risk_score)) if risk_score is not None else None
        risk_level = _clean_text(risk_payload.get("risk_level") or extra.get("risk_level") or "LOW").upper()
        if risk_level not in _RISK_ORDER and risk_score is not None:
            risk_level = "HIGH" if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.4 else "LOW"

        signals: dict[str, MetricSignal] = {}
        for name, spec in _METRIC_SPECS.items():
            current = _first_float(feature_payload, spec["aliases"])
            baseline = _first_float(feature_payload, spec["baseline_aliases"])
            trend = "stable"
            if baseline is None:
                for vital_key in spec["vital_keys"]:
                    vital = vitals.get(vital_key)
                    if isinstance(vital, dict):
                        baseline = _safe_float(vital.get("avg_7d")) or _safe_float(vital.get("baseline"))
                        current = current if current is not None else _safe_float(vital.get("latest"))
                        trend = _clean_text(vital.get("trend") or trend).lower() or "stable"
                        break
            if current is None:
                current = _first_float(wearable_trends, spec["aliases"])
            status, delta_pct, delta = _metric_status(current, baseline, bool(spec.get("lower_is_better")))
            if current is None and baseline is None:
                continue
            signals[name] = MetricSignal(
                name=name,
                label=str(spec["label"]),
                current=current,
                baseline=baseline,
                trend=trend,
                unit=str(spec["unit"]),
                status=status,
                delta=delta,
                delta_pct=delta_pct,
                lower_is_better=bool(spec.get("lower_is_better")),
                evidence=[
                    f"Current {spec['label'].lower()} {current:g}{spec['unit']}".strip() if current is not None else "",
                    (
                        f"Recent baseline {baseline:g}{spec['unit']}".strip()
                        if baseline is not None
                        else ""
                    ),
                ],
            )

        analysis = clinical_history.get("analysis") if isinstance(clinical_history.get("analysis"), dict) else {}
        continuity = user_context.get("continuity_summary") if isinstance(user_context.get("continuity_summary"), dict) else {}
        longitudinal = user_context.get("longitudinal_summary") if isinstance(user_context.get("longitudinal_summary"), dict) else {}
        memory = {
            "major_trends": longitudinal.get("major_trends") or [],
            "abnormal_changes": longitudinal.get("abnormal_changes") or [],
            "persistent_issues": longitudinal.get("persistent_issues") or [],
            "recommendation_carryover": longitudinal.get("recommendation_carryover") or [],
            "ongoing_symptoms": continuity.get("ongoing_symptoms") or [],
            "carryover_recommendations": continuity.get("carryover_recommendations") or [],
            "recent_assistant_focus": continuity.get("recent_assistant_focus") or [],
            "last_persona": continuity.get("last_persona") or "",
        }

        symptoms = unique_texts(
            [
                *(analysis.get("symptoms") or []),
                *(clinical_history.get("associated_symptoms") or []),
                *(continuity.get("ongoing_symptoms") or []),
                *(clinical_history.get("symptoms") or []),
            ],
            limit=10,
        )
        labs = [row for row in (labs or []) if isinstance(row, dict)]
        if not labs and isinstance(extra.get("lab_results"), list):
            labs = [row for row in extra["lab_results"] if isinstance(row, dict)]

        drivers = [row for row in (drivers or []) if isinstance(row, dict)]
        shap_values = [row for row in (shap_values or []) if isinstance(row, dict)]
        anomalies = [row for row in (anomalies or []) if isinstance(row, dict)]
        if not anomalies:
            anomalies = self._derive_anomalies(signals=signals, labs=labs, forecasting=forecasting)

        forecast_windows = forecasting.get("forecast") if isinstance(forecasting.get("forecast"), dict) else {}

        tags = unique_texts(
            [
                risk_level.lower(),
                *symptoms[:3],
                *[row.get("feature_name") or row.get("title") for row in drivers[:3]],
            ],
            limit=8,
        )

        return NarrativeContext(
            user_id=user_id,
            workflow=workflow,
            source=source,
            risk_score=risk_score,
            risk_level=risk_level or "LOW",
            risk_scores=risk_scores,
            feature_payload=feature_payload,
            vitals=vitals,
            wearable_trends=wearable_trends,
            forecasting=forecasting,
            clinical_history=clinical_history,
            conversation_history=[row for row in (conversation_history or []) if isinstance(row, dict)],
            drivers=drivers,
            shap_values=shap_values,
            anomalies=anomalies,
            labs=labs,
            ocr_summary=dict(ocr_summary or {}),
            recommendations=list(recommendations or []),
            recommendation_plans=list(recommendation_plans or []),
            symptoms=symptoms,
            signals=signals,
            longitudinal_summary=longitudinal,
            continuity_summary=continuity,
            memory=memory,
            disease_simulation=dict(disease_simulation or {}),
            recent_events=[row for row in user_context.get("recent_events", []) if isinstance(row, dict)],
            report_summaries=[row for row in user_context.get("report_summaries", []) if isinstance(row, dict)],
            forecast_windows=forecast_windows,
            tags=tags,
        )

    def _derive_anomalies(
        self,
        *,
        signals: dict[str, MetricSignal],
        labs: list[dict[str, Any]],
        forecasting: dict[str, Any],
    ) -> list[dict[str, Any]]:
        derived: list[dict[str, Any]] = []
        for signal in signals.values():
            if signal.status not in {"elevated", "reduced"}:
                continue
            derived.append(
                {
                    "title": f"{signal.label} shifted from baseline",
                    "summary": (
                        f"{signal.label} is {signal.formatted_current()} compared with a usual baseline near "
                        f"{signal.formatted_baseline()}."
                    ).strip(),
                    "severity": "high" if abs(signal.delta_pct or 0.0) >= 0.18 else "medium",
                    "metric": signal.name,
                }
            )
        for lab in labs:
            status = _clean_text(lab.get("status")).lower()
            if status not in {"high", "low", "abnormal", "critical"}:
                continue
            name = _clean_text(lab.get("name") or lab.get("test_name") or "Lab marker")
            derived.append(
                {
                    "title": f"{name} flagged {status}",
                    "summary": _clean_text(lab.get("summary") or lab.get("interpretation") or lab.get("reference_range")),
                    "severity": "high" if status == "critical" else "medium",
                    "metric": name.lower().replace(" ", "_"),
                }
            )
        forecast = forecasting.get("forecast") if isinstance(forecasting.get("forecast"), dict) else {}
        for window, payload in forecast.items():
            if not isinstance(payload, dict):
                continue
            summary = _clean_text(payload.get("summary")).lower()
            if any(token in summary for token in ("worsen", "decline", "instability", "deterior")):
                derived.append(
                    {
                        "title": f"Projected instability in {window}",
                        "summary": _clean_text(payload.get("summary")),
                        "severity": "medium",
                        "metric": f"forecast_{window}",
                    }
                )
        return derived[:8]
