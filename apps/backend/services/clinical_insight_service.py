from __future__ import annotations

from typing import Any


class ClinicalInsightService:
    CONDITION_LABELS = {
        "cardiovascular": "cardiovascular disease",
        "diabetes": "type 2 diabetes",
        "respiratory": "respiratory disease",
    }

    @staticmethod
    def _safe_float(value: Any, default: float | None = None) -> float | None:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _titleize(value: str | None) -> str:
        parts = [part for part in str(value or "").replace("-", "_").split("_") if part]
        return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts) or "Health driver"

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _normalize_risk_map(risk_map: dict[str, Any] | None) -> dict[str, float]:
        payload = risk_map if isinstance(risk_map, dict) else {}
        normalized: dict[str, float] = {}
        for key in ("cardiovascular", "diabetes", "respiratory"):
            raw = ClinicalInsightService._safe_float(payload.get(key), 0.0) or 0.0
            normalized[key] = ClinicalInsightService._clamp(raw / 100.0 if raw > 1 else raw)
        return normalized

    @staticmethod
    def _normalize_delta_map(delta_map: dict[str, Any] | None) -> dict[str, float]:
        payload = delta_map if isinstance(delta_map, dict) else {}
        normalized: dict[str, float] = {}
        for key in ("cardiovascular", "diabetes", "respiratory"):
            raw = ClinicalInsightService._safe_float(payload.get(key), 0.0) or 0.0
            normalized[key] = raw / 100.0 if abs(raw) > 1 else raw
        return normalized

    @staticmethod
    def _dedupe_text(items: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for item in items:
            text = ClinicalInsightService._clean_text(item)
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(text)
        return deduped

    @staticmethod
    def _priority_from_risk(risk_value: float, *, worsening: bool = False) -> str:
        if worsening or risk_value >= 0.7:
            return "high"
        if risk_value >= 0.35:
            return "medium"
        return "low"

    @staticmethod
    def build_outcome(
        *,
        risk_map: dict[str, Any] | None,
        focus_condition: str = "cardiovascular",
        delta_map: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_risks = ClinicalInsightService._normalize_risk_map(risk_map)
        normalized_delta = ClinicalInsightService._normalize_delta_map(delta_map)
        focus = focus_condition if focus_condition in normalized_risks else "cardiovascular"
        risk_value = normalized_risks.get(focus, 0.0)
        delta_value = normalized_delta.get(focus, 0.0)
        condition_label = ClinicalInsightService.CONDITION_LABELS.get(focus, focus.replace("_", " "))

        if risk_value > 0.7:
            headline = f"High probability of developing {condition_label}"
            severity = "high"
            summary = "High risk, prompt preventive action and clinical review are advisable."
        elif risk_value >= 0.3:
            headline = "Moderate risk, preventive measures required"
            severity = "moderate"
            summary = f"The current profile shows a meaningful risk signal for {condition_label} that should be actively reduced."
        else:
            headline = "Low risk"
            severity = "low"
            summary = f"The current profile is in a relatively low-risk range for {condition_label}, but continued prevention still matters."

        if delta_value <= -0.05:
            summary = f"{summary} The simulated scenario improves the outlook compared with baseline."
        elif delta_value >= 0.05:
            summary = f"{summary} The simulated scenario worsens the outlook compared with baseline."

        return {
            "focus_condition": focus,
            "severity": severity,
            "risk_score": round(risk_value, 4),
            "headline": headline,
            "summary": summary,
        }

    @staticmethod
    def build_symptoms(
        *,
        feature_payload: dict[str, Any] | None,
        risk_map: dict[str, Any] | None = None,
    ) -> list[str]:
        features = feature_payload if isinstance(feature_payload, dict) else {}
        risks = ClinicalInsightService._normalize_risk_map(risk_map)
        systolic_bp = ClinicalInsightService._safe_float(features.get("systolic_bp"))
        diastolic_bp = ClinicalInsightService._safe_float(features.get("diastolic_bp"))
        steps = ClinicalInsightService._safe_float(features.get("activity_level") or features.get("steps"))
        sleep = ClinicalInsightService._safe_float(features.get("sleep_duration") or features.get("sleep"))
        heart_rate = ClinicalInsightService._safe_float(
            features.get("avg_rhr")
            or features.get("hr_mean_7d")
            or features.get("heart_rate")
        )

        symptoms: list[str] = []
        if (systolic_bp or 0) >= 130 or (diastolic_bp or 0) >= 80:
            symptoms.extend(["Headache", "Dizziness"])
        if (steps or 0) < 5000:
            symptoms.extend(["Fatigue", "Reduced exercise tolerance"])
        if (sleep or 0) < 6.5:
            symptoms.extend(["Daytime fatigue", "Daytime cognitive slowing"])
        if (heart_rate or 0) >= 90:
            symptoms.extend(["Palpitations", "Low exercise tolerance"])
        if risks.get("respiratory", 0.0) >= 0.65:
            symptoms.extend(["Shortness of breath", "Reduced stamina"])

        return ClinicalInsightService._dedupe_text(symptoms)[:6]

    @staticmethod
    def build_possible_conditions(
        *,
        feature_payload: dict[str, Any] | None,
        risk_map: dict[str, Any] | None = None,
    ) -> list[str]:
        features = feature_payload if isinstance(feature_payload, dict) else {}
        risks = ClinicalInsightService._normalize_risk_map(risk_map)
        systolic_bp = ClinicalInsightService._safe_float(features.get("systolic_bp"))
        diastolic_bp = ClinicalInsightService._safe_float(features.get("diastolic_bp"))
        bmi = ClinicalInsightService._safe_float(features.get("bmi"))
        glucose = ClinicalInsightService._safe_float(features.get("glucose"))
        steps = ClinicalInsightService._safe_float(features.get("activity_level") or features.get("steps"))
        sleep = ClinicalInsightService._safe_float(features.get("sleep_duration") or features.get("sleep"))
        heart_rate = ClinicalInsightService._safe_float(
            features.get("avg_rhr")
            or features.get("hr_mean_7d")
            or features.get("heart_rate")
        )

        conditions: list[str] = []
        if (systolic_bp or 0) >= 130 or (diastolic_bp or 0) >= 80:
            conditions.append("Hypertension risk")
        if (glucose or 0) >= 100 or risks.get("diabetes", 0.0) >= 0.55 or (bmi or 0) >= 30:
            conditions.append("Type 2 diabetes risk")
        if risks.get("cardiovascular", 0.0) >= 0.55 or (steps or 0) < 6000 or (systolic_bp or 0) >= 130:
            conditions.append("Cardiovascular disease risk")
        if risks.get("respiratory", 0.0) >= 0.6 or ((sleep or 0) < 6 and (heart_rate or 0) >= 90):
            conditions.append("Respiratory strain")

        if not conditions:
            conditions.append("No dominant condition signal detected")

        return ClinicalInsightService._dedupe_text(conditions)[:5]

    @staticmethod
    def build_recommendations(
        *,
        feature_payload: dict[str, Any] | None,
        risk_map: dict[str, Any] | None = None,
        delta_map: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        features = feature_payload if isinstance(feature_payload, dict) else {}
        risks = ClinicalInsightService._normalize_risk_map(risk_map)
        deltas = ClinicalInsightService._normalize_delta_map(delta_map)
        overall_risk = max(risks.values(), default=0.0)

        systolic_bp = ClinicalInsightService._safe_float(features.get("systolic_bp"))
        diastolic_bp = ClinicalInsightService._safe_float(features.get("diastolic_bp"))
        steps = ClinicalInsightService._safe_float(features.get("activity_level") or features.get("steps"))
        sleep = ClinicalInsightService._safe_float(features.get("sleep_duration") or features.get("sleep"))
        heart_rate = ClinicalInsightService._safe_float(
            features.get("avg_rhr")
            or features.get("hr_mean_7d")
            or features.get("heart_rate")
        )
        bmi = ClinicalInsightService._safe_float(features.get("bmi"))
        glucose = ClinicalInsightService._safe_float(features.get("glucose"))

        recommendations: list[dict[str, Any]] = []

        if (systolic_bp or 0) >= 130 or (diastolic_bp or 0) >= 80:
            worsening = deltas.get("cardiovascular", 0.0) > 0.0
            recommendations.append(
                {
                    "title": "Lower blood pressure burden",
                    "description": "Reduce sodium intake, monitor home blood pressure regularly, and keep follow-up readings consistent.",
                    "category": "lifestyle",
                    "priority": ClinicalInsightService._priority_from_risk(risks.get("cardiovascular", overall_risk), worsening=worsening),
                    "feature": "blood_pressure",
                }
            )

        if (steps or 0) < 8000:
            worsening = deltas.get("cardiovascular", 0.0) > 0.0 or deltas.get("diabetes", 0.0) > 0.0
            recommendations.append(
                {
                    "title": "Increase daily activity",
                    "description": "Work toward at least 8,000 daily steps or equivalent moderate activity to improve cardiovascular and metabolic resilience.",
                    "category": "fitness",
                    "priority": ClinicalInsightService._priority_from_risk(max(risks.get("cardiovascular", 0.0), risks.get("diabetes", 0.0)), worsening=worsening),
                    "feature": "steps",
                }
            )

        if (sleep or 0) < 7.0:
            worsening = deltas.get("cardiovascular", 0.0) > 0.0 or deltas.get("respiratory", 0.0) > 0.0
            recommendations.append(
                {
                    "title": "Improve sleep hygiene",
                    "description": "Protect a stable sleep window, reduce late caffeine and screens, and aim for at least 7 hours of nightly sleep.",
                    "category": "sleep",
                    "priority": ClinicalInsightService._priority_from_risk(max(risks.get("cardiovascular", 0.0), risks.get("respiratory", 0.0)), worsening=worsening),
                    "feature": "sleep",
                }
            )

        if (heart_rate or 0) >= 90:
            recommendations.append(
                {
                    "title": "Reduce sustained heart-rate strain",
                    "description": "Limit stimulant excess, improve aerobic conditioning gradually, and reassess resting heart rate after recovery improves.",
                    "category": "fitness",
                    "priority": ClinicalInsightService._priority_from_risk(risks.get("cardiovascular", overall_risk)),
                    "feature": "heart_rate",
                }
            )

        if (bmi or 0) >= 27:
            recommendations.append(
                {
                    "title": "Reduce metabolic load",
                    "description": "A gradual, sustainable weight reduction can lower both diabetes and cardiovascular risk more effectively than aggressive short-term restriction.",
                    "category": "diet",
                    "priority": ClinicalInsightService._priority_from_risk(max(risks.get("cardiovascular", 0.0), risks.get("diabetes", 0.0))),
                    "feature": "bmi",
                }
            )

        if (glucose or 0) >= 100:
            recommendations.append(
                {
                    "title": "Stabilize blood sugar patterns",
                    "description": "Favor higher-fiber meals, reduce refined carbohydrates, and add post-meal movement to improve glucose handling.",
                    "category": "diet",
                    "priority": ClinicalInsightService._priority_from_risk(risks.get("diabetes", overall_risk)),
                    "feature": "glucose",
                }
            )

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in recommendations:
            key = f"{item.get('feature')}::{ClinicalInsightService._clean_text(item.get('title')).lower()}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        if deduped:
            return deduped[:5]

        return [
            {
                "title": "Maintain current preventive habits",
                "description": "The current feature pattern is comparatively stable. Continue monitoring and maintain consistent sleep, activity, and blood-pressure habits.",
                "category": "lifestyle",
                "priority": ClinicalInsightService._priority_from_risk(overall_risk),
                "feature": "overall_health",
            }
        ]

    @staticmethod
    def build_key_drivers(
        *,
        shap_values: list[dict[str, Any]] | None,
        feature_payload: dict[str, Any] | None,
        risk_map: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        features = feature_payload if isinstance(feature_payload, dict) else {}
        risks = ClinicalInsightService._normalize_risk_map(risk_map)
        drivers: list[dict[str, Any]] = []

        for item in shap_values or []:
            feature_name = ClinicalInsightService._clean_text(item.get("feature_name"))
            if not feature_name:
                continue
            impact = ClinicalInsightService._safe_float(
                item.get("shap_value"),
                ClinicalInsightService._safe_float(item.get("impact"), 0.0),
            ) or 0.0
            description = ClinicalInsightService._clean_text(
                item.get("explanation")
                or item.get("description")
                or item.get("shap_payload", {}).get("explanation")
            )
            drivers.append(
                {
                    "feature_name": feature_name,
                    "title": ClinicalInsightService._titleize(feature_name),
                    "impact": round(impact, 4),
                    "direction": "increase" if impact >= 0 else "decrease",
                    "description": description,
                    "source": "shap",
                }
            )

        systolic_bp = ClinicalInsightService._safe_float(features.get("systolic_bp"))
        diastolic_bp = ClinicalInsightService._safe_float(features.get("diastolic_bp"))
        if (systolic_bp or 0) >= 130 or (diastolic_bp or 0) >= 80:
            drivers.append(
                {
                    "feature_name": "blood_pressure",
                    "title": "Blood Pressure",
                    "impact": round(max(risks.get("cardiovascular", 0.0), 0.2), 4),
                    "direction": "increase",
                    "description": f"Blood pressure at {int(systolic_bp or 0)}/{int(diastolic_bp or 0)} mmHg is above the protective range and increases vascular strain.",
                    "source": "threshold_rule",
                }
            )

        sorted_drivers = sorted(drivers, key=lambda item: abs(float(item.get("impact") or 0.0)), reverse=True)
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in sorted_drivers:
            key = ClinicalInsightService._clean_text(item.get("feature_name")).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:5]

    @staticmethod
    def enrich_payload(
        *,
        feature_payload: dict[str, Any] | None,
        risk_map: dict[str, Any] | None,
        shap_values: list[dict[str, Any]] | None = None,
        focus_condition: str = "cardiovascular",
        delta_map: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        outcome = ClinicalInsightService.build_outcome(
            risk_map=risk_map,
            focus_condition=focus_condition,
            delta_map=delta_map,
        )
        recommendations = ClinicalInsightService.build_recommendations(
            feature_payload=feature_payload,
            risk_map=risk_map,
            delta_map=delta_map,
        )
        return {
            "outcome": outcome,
            "symptoms": ClinicalInsightService.build_symptoms(
                feature_payload=feature_payload,
                risk_map=risk_map,
            ),
            "possible_conditions": ClinicalInsightService.build_possible_conditions(
                feature_payload=feature_payload,
                risk_map=risk_map,
            ),
            "key_drivers": ClinicalInsightService.build_key_drivers(
                shap_values=shap_values,
                feature_payload=feature_payload,
                risk_map=risk_map,
            ),
            "recommendations": recommendations,
            "summary": outcome["summary"],
        }
