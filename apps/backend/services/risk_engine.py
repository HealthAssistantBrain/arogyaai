from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.feature_service import FeatureSnapshot, _clamp


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _risk_level(score: float) -> str:
    if score >= 65.0:
        return "CRITICAL"
    if score >= 45.0:
        return "HIGH"
    if score >= 25.0:
        return "MODERATE"
    return "LOW"


def _risk_label(level: str) -> str:
    labels = {
        "LOW": "Low",
        "MODERATE": "Moderate",
        "HIGH": "High",
        "CRITICAL": "Critical",
    }
    return labels.get(level, "Unknown")


def _impact_text(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}"


def _clamp_contribution(value: float, weight: float) -> float:
    return _clamp(value, -weight, weight)


def _feature_value(features: Any, *keys: str) -> Any:
    if isinstance(features, dict):
        for key in keys:
            if key in features:
                return features.get(key)
        return None

    for key in keys:
        if hasattr(features, key):
            return getattr(features, key)
    return None


def is_data_sufficient(features: Any) -> bool:
    required = {
        "age": ("age",),
        "hrv": ("avg_hrv", "hrv"),
        "activity": ("activity_level", "activity"),
        "sleep": ("sleep_score", "sleep_duration", "sleep"),
    }
    return all(_feature_value(features, *aliases) is not None for aliases in required.values())


def _has_valid_model() -> bool:
    model_path = os.getenv("AI_INSIGHTS_MODEL_PATH", "").strip()
    if not model_path:
        return False
    return Path(model_path).expanduser().is_file()


def _linear_contribution(
    value: float | None,
    *,
    target: float,
    span: float,
    weight: float,
    worse_when_high: bool = True,
) -> float:
    if value is None:
        return 0.0

    if span <= 0:
        return 0.0

    if worse_when_high:
        raw = (value - target) / span * weight
    else:
        raw = (target - value) / span * weight
    return round(_clamp_contribution(raw, weight), 1)


@dataclass
class DriverAggregate:
    key: str
    label: str
    contribution: float = 0.0
    domains: set[str] | None = None
    detail: str = ""
    value: Any = None

    def add(self, domain: str, contribution: float, detail: str, value: Any = None) -> None:
        self.contribution += contribution
        if self.domains is None:
            self.domains = set()
        self.domains.add(domain)
        if not self.detail:
            self.detail = detail
        elif detail and detail not in self.detail:
            self.detail = f"{self.detail} {detail}".strip()
        if value is not None and self.value is None:
            self.value = value

    def to_dict(self) -> dict[str, Any]:
        domains = sorted(self.domains or [])
        return {
            "key": self.key,
            "label": self.label,
            "contribution": round(self.contribution, 1),
            "impact": _impact_text(self.contribution),
            "direction": "increasing" if self.contribution >= 0 else "decreasing",
            "domains": domains,
            "detail": self.detail,
            "value": self.value,
        }


class RiskEngine:
    @staticmethod
    def _card(
        key: str,
        label: str,
        score: float,
        contributing_factors: list[dict[str, Any]],
        summary: str,
    ) -> dict[str, Any]:
        level = _risk_level(score)
        delta_from_neutral = round(score - 50.0, 1)
        return {
            "key": key,
            "label": label,
            "score": round(score, 1),
            "risk_level": level,
            "risk_label": _risk_label(level),
            "status": _risk_label(level),
            "progress": round(_clamp(score, 0.0, 100.0), 1),
            "delta_from_neutral": delta_from_neutral,
            "trend": f"{'+' if delta_from_neutral >= 0 else '-'}{abs(delta_from_neutral):.1f}% vs neutral",
            "summary": summary,
            "drivers": contributing_factors[:4],
        }

    @staticmethod
    def _format_analysis(highest_card: dict[str, Any], cards: list[dict[str, Any]], drivers: list[dict[str, Any]], features: FeatureSnapshot) -> str:
        top_card = highest_card
        secondary = next((card for card in cards if card["key"] != top_card["key"]), None)
        strongest_driver = drivers[0] if drivers else None
        second_driver = drivers[1] if len(drivers) > 1 else None

        lead = (
            f"{top_card['label']} risk is the dominant signal at {top_card['score']:.1f}% ({top_card['risk_label'].lower()}). "
            f"{top_card['summary']}"
        )
        if secondary:
            lead += f" {secondary['label']} remains the next most important trackable domain at {secondary['score']:.1f}%."

        if strongest_driver:
            lead += (
                f" The strongest overall driver is {strongest_driver['label'].lower()} ({strongest_driver['impact']}), "
                f"which affects {', '.join(strongest_driver['domains'])}."
            )
        if second_driver:
            lead += f" {second_driver['label']} ({second_driver['impact']}) is the next biggest modifier."

        if features.notes:
            lead += f" {' '.join(features.notes)}"
        return lead

    @staticmethod
    def _recommendations(features: FeatureSnapshot, cards: list[dict[str, Any]], drivers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        top_risk = cards[0] if cards else None

        if features.sleep_score is not None and features.sleep_score < 72:
            recommendations.append(
                {
                    "title": "Stabilize sleep quality",
                    "detail": "Protect a consistent 7.5 to 8.5 hour sleep window, reduce late screens, and keep wake time fixed to improve recovery and lower vascular strain.",
                    "priority": "high" if top_risk and top_risk["key"] in {"hypertension", "cad"} else "medium",
                    "category": "sleep",
                }
            )

        if features.sleep_duration is not None and features.sleep_duration < 7.0:
            recommendations.append(
                {
                    "title": "Increase sleep duration",
                    "detail": "Add 30 to 60 minutes of sleep opportunity for several nights in a row. That usually improves HRV and reduces downstream cardiometabolic load.",
                    "priority": "high" if top_risk and top_risk["key"] == "hypertension" else "medium",
                    "category": "sleep",
                }
            )

        if features.activity_level is not None and features.activity_level < 7500:
            recommendations.append(
                {
                    "title": "Raise daily movement",
                    "detail": "Move toward 8,000 to 10,000 steps per day or equivalent active time. More movement lowers diabetes and CAD burden by improving insulin sensitivity and vascular health.",
                    "priority": "high" if top_risk and top_risk["key"] == "diabetes" else "medium",
                    "category": "activity",
                }
            )

        if features.systolic_bp is not None or features.diastolic_bp is not None:
            if (features.systolic_bp or 0) >= 130 or (features.diastolic_bp or 0) >= 80:
                recommendations.append(
                    {
                        "title": "Monitor blood pressure closely",
                        "detail": "Repeat BP readings at a consistent time of day, reduce sodium-heavy meals, and escalate to clinician review if elevated readings persist.",
                        "priority": "high",
                        "category": "cardiovascular",
                    }
                )

        if features.bmi is not None and features.bmi >= 25:
            recommendations.append(
                {
                    "title": "Reduce metabolic load",
                    "detail": "A modest weight reduction can materially lower diabetes and CAD risk. Pair calorie control with movement rather than aggressive short-term restriction.",
                    "priority": "medium",
                    "category": "metabolic",
                }
            )

        if features.cholesterol_proxy is not None and features.cholesterol_proxy >= 115:
            recommendations.append(
                {
                    "title": "Review lipid risk pattern",
                    "detail": "The LDL proxy is elevated enough to keep CAD risk up. A formal lipid panel would help confirm whether the surrogate is tracking a true atherogenic load.",
                    "priority": "medium",
                    "category": "cardiovascular",
                }
            )

        if features.avg_hrv is not None and features.avg_hrv < 46:
            recommendations.append(
                {
                    "title": "Support autonomic recovery",
                    "detail": "Lower training intensity for a few days, breathe slower, and keep evenings calmer. HRV tends to improve when stress and sleep debt are addressed together.",
                    "priority": "medium",
                    "category": "recovery",
                }
            )

        return recommendations[:5]

    @staticmethod
    def _empty_payload(features: FeatureSnapshot, user_id: str | None = None) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "status": "insufficient_data",
            "risks": {},
            "drivers": [],
            "analysis": None,
            "recommendations": [],
            "last_updated": None,
            "confidence": 0.0,
            "data_points": 0,
            "feature_snapshot": {},
        }

    @staticmethod
    def evaluate(features: FeatureSnapshot, user_id: str | None = None) -> dict[str, Any]:
        if not is_data_sufficient(features) or not _has_valid_model():
            return RiskEngine._empty_payload(features, user_id=user_id)

        hrv = features.avg_hrv
        rhr = features.avg_rhr
        sleep_score = features.sleep_score
        sleep_duration = features.sleep_duration
        activity = features.activity_level
        bmi = features.bmi
        sys_bp = features.systolic_bp
        dia_bp = features.diastolic_bp
        age = features.age
        ldl_proxy = features.cholesterol_proxy

        aggregates: dict[str, DriverAggregate] = {
            "blood_pressure": DriverAggregate(key="blood_pressure", label="High Blood Pressure"),
            "low_hrv": DriverAggregate(key="low_hrv", label="Low HRV"),
            "sleep_consistency": DriverAggregate(key="sleep_consistency", label="Sleep Consistency"),
            "low_activity": DriverAggregate(key="low_activity", label="Low Activity"),
            "high_bmi": DriverAggregate(key="high_bmi", label="High BMI"),
            "cholesterol_proxy": DriverAggregate(key="cholesterol_proxy", label="LDL Proxy"),
            "age_risk": DriverAggregate(key="age_risk", label="Age Load"),
            "resting_hr": DriverAggregate(key="resting_hr", label="Elevated Resting Heart Rate"),
        }

        def add_driver(key: str, domain: str, contribution: float, detail: str, value: Any = None) -> None:
            if abs(contribution) < 0.05:
                return
            aggregates[key].add(domain, round(contribution, 1), detail, value=value)

        diabetes_components = {
            "high_bmi": _linear_contribution(bmi, target=24.5, span=6.0, weight=12.0, worse_when_high=True),
            "low_activity": _linear_contribution(activity, target=8500.0, span=5500.0, weight=12.0, worse_when_high=False),
            "sleep_consistency": _linear_contribution(sleep_duration, target=7.5, span=2.0, weight=6.0, worse_when_high=False)
            + _linear_contribution(sleep_score, target=78.0, span=20.0, weight=4.0, worse_when_high=False),
            "low_hrv": _linear_contribution(hrv, target=52.0, span=20.0, weight=4.0, worse_when_high=False),
            "age_risk": _linear_contribution(age, target=40.0, span=20.0, weight=3.0, worse_when_high=True),
            "blood_pressure": _linear_contribution(sys_bp, target=120.0, span=20.0, weight=2.0, worse_when_high=True),
        }
        diabetes_score = 34.0 + sum(diabetes_components.values())

        hypertension_components = {
            "blood_pressure": _linear_contribution(sys_bp, target=118.0, span=22.0, weight=14.0, worse_when_high=True)
            + _linear_contribution(dia_bp, target=76.0, span=14.0, weight=10.0, worse_when_high=True),
            "low_hrv": _linear_contribution(hrv, target=52.0, span=18.0, weight=10.0, worse_when_high=False),
            "sleep_consistency": _linear_contribution(sleep_score, target=78.0, span=18.0, weight=6.0, worse_when_high=False)
            + _linear_contribution(sleep_duration, target=7.5, span=1.8, weight=4.0, worse_when_high=False),
            "resting_hr": _linear_contribution(rhr, target=60.0, span=15.0, weight=6.0, worse_when_high=True),
            "high_bmi": _linear_contribution(bmi, target=24.5, span=5.0, weight=5.0, worse_when_high=True),
            "low_activity": _linear_contribution(activity, target=8000.0, span=5000.0, weight=3.0, worse_when_high=False),
            "age_risk": _linear_contribution(age, target=40.0, span=18.0, weight=4.0, worse_when_high=True),
        }
        hypertension_score = 28.0 + sum(hypertension_components.values())

        cad_components = {
            "cholesterol_proxy": _linear_contribution(ldl_proxy, target=110.0, span=28.0, weight=14.0, worse_when_high=True),
            "blood_pressure": _linear_contribution(sys_bp, target=118.0, span=20.0, weight=10.0, worse_when_high=True)
            + _linear_contribution(dia_bp, target=76.0, span=12.0, weight=6.0, worse_when_high=True),
            "low_hrv": _linear_contribution(hrv, target=52.0, span=18.0, weight=10.0, worse_when_high=False),
            "low_activity": _linear_contribution(activity, target=8000.0, span=5000.0, weight=7.0, worse_when_high=False),
            "high_bmi": _linear_contribution(bmi, target=24.5, span=5.0, weight=6.0, worse_when_high=True),
            "sleep_consistency": _linear_contribution(sleep_score, target=78.0, span=18.0, weight=4.0, worse_when_high=False)
            + _linear_contribution(sleep_duration, target=7.5, span=1.8, weight=3.0, worse_when_high=False),
            "age_risk": _linear_contribution(age, target=40.0, span=18.0, weight=4.0, worse_when_high=True),
        }
        cad_score = 30.0 + sum(cad_components.values())

        diabetes_score = round(_clamp(diabetes_score, 0.0, 100.0), 1)
        hypertension_score = round(_clamp(hypertension_score, 0.0, 100.0), 1)
        cad_score = round(_clamp(cad_score, 0.0, 100.0), 1)

        diabetes_drivers = [
            {
                "label": "High BMI",
                "contribution": diabetes_components["high_bmi"],
                "detail": "Higher body mass nudges insulin resistance upward.",
            },
            {
                "label": "Low Activity",
                "contribution": diabetes_components["low_activity"],
                "detail": "Lower step volume weakens glucose handling and metabolic flexibility.",
            },
            {
                "label": "Sleep Consistency",
                "contribution": diabetes_components["sleep_consistency"],
                "detail": "Sleep duration and sleep score influence glucose regulation and appetite control.",
            },
            {
                "label": "Low HRV",
                "contribution": diabetes_components["low_hrv"],
                "detail": "Recovery strain remains a smaller but relevant metabolic modifier.",
            },
        ]

        hypertension_drivers = [
            {
                "label": "High Blood Pressure",
                "contribution": hypertension_components["blood_pressure"],
                "detail": "Recent systolic and diastolic readings sit above the protective range.",
            },
            {
                "label": "Low HRV",
                "contribution": hypertension_components["low_hrv"],
                "detail": "Reduced autonomic recovery keeps vascular tone elevated.",
            },
            {
                "label": "Sleep Consistency",
                "contribution": hypertension_components["sleep_consistency"],
                "detail": "Short or fragmented sleep increases sympathetic load.",
            },
            {
                "label": "Elevated Resting Heart Rate",
                "contribution": hypertension_components["resting_hr"],
                "detail": "Resting heart rate is still running a bit hot relative to the target band.",
            },
        ]

        cad_drivers = [
            {
                "label": "LDL Proxy",
                "contribution": cad_components["cholesterol_proxy"],
                "detail": "The surrogate lipid load is elevated from BMI, BP, activity, and recovery patterns.",
            },
            {
                "label": "High Blood Pressure",
                "contribution": cad_components["blood_pressure"],
                "detail": "Pressure load is one of the strongest vascular inputs for CAD risk.",
            },
            {
                "label": "Low HRV",
                "contribution": cad_components["low_hrv"],
                "detail": "Lower HRV implies less recovery reserve for the cardiovascular system.",
            },
            {
                "label": "Low Activity",
                "contribution": cad_components["low_activity"],
                "detail": "Insufficient movement keeps coronary risk from falling as quickly as it could.",
            },
        ]

        for key, contribution in diabetes_components.items():
            if key == "blood_pressure":
                detail = "Blood pressure nudges metabolic strain and insulin resistance upward."
                value = sys_bp
            elif key == "high_bmi":
                detail = "BMI is above the ideal range for stable glucose handling."
                value = bmi
            elif key == "low_activity":
                detail = "Lower movement reduces insulin sensitivity."
                value = activity
            elif key == "sleep_consistency":
                detail = "Sleep duration and sleep score both shape glucose control."
                value = sleep_score
            elif key == "low_hrv":
                detail = "Lower recovery reserve can worsen metabolic control."
                value = hrv
            else:
                detail = "Age adds background metabolic pressure."
                value = age
            add_driver(key, "diabetes", contribution, detail, value)

        for key, contribution in hypertension_components.items():
            if key == "blood_pressure":
                detail = "Recent blood pressure readings are above the optimal band."
                value = f"{sys_bp}/{dia_bp}" if sys_bp is not None or dia_bp is not None else None
            elif key == "low_hrv":
                detail = "Lower HRV suggests more sympathetic stress."
                value = hrv
            elif key == "sleep_consistency":
                detail = "Sleep quality and duration are not fully protective yet."
                value = sleep_score
            elif key == "resting_hr":
                detail = "Resting heart rate is still elevated relative to the target range."
                value = rhr
            elif key == "high_bmi":
                detail = "BMI adds vascular strain."
                value = bmi
            elif key == "low_activity":
                detail = "Lower activity keeps blood pressure control from improving."
                value = activity
            else:
                detail = "Age increases long-term vascular load."
                value = age
            add_driver(key, "hypertension", contribution, detail, value)

        for key, contribution in cad_components.items():
            if key == "cholesterol_proxy":
                detail = "The LDL surrogate is elevated enough to matter for coronary plaque burden."
                value = ldl_proxy
            elif key == "blood_pressure":
                detail = "Vascular pressure load is a major CAD amplifier."
                value = f"{sys_bp}/{dia_bp}" if sys_bp is not None or dia_bp is not None else None
            elif key == "low_hrv":
                detail = "Lower HRV reduces cardiovascular recovery reserve."
                value = hrv
            elif key == "low_activity":
                detail = "Lower movement suppresses lipid handling and vascular conditioning."
                value = activity
            elif key == "high_bmi":
                detail = "BMI contributes to atherogenic burden."
                value = bmi
            elif key == "sleep_consistency":
                detail = "Sleep consistency supports vascular recovery and lipid control."
                value = sleep_score
            else:
                detail = "Age raises baseline coronary susceptibility."
                value = age
            add_driver(key, "cad", contribution, detail, value)

        cards = [
            RiskEngine._card(
                "diabetes",
                "Diabetes",
                diabetes_score,
                diabetes_drivers,
                "BMI and activity are the main diabetes levers, with sleep quality and HRV acting as secondary modifiers.",
            ),
            RiskEngine._card(
                "hypertension",
                "Hypertension",
                hypertension_score,
                hypertension_drivers,
                "Blood pressure is the leading signal, with HRV, sleep, and resting heart rate adding clear context.",
            ),
            RiskEngine._card(
                "cad",
                "CAD",
                cad_score,
                cad_drivers,
                "The coronary estimate is pushed by the LDL proxy, vascular pressure, and recovery quality.",
            ),
        ]
        cards.sort(key=lambda item: item["score"], reverse=True)

        aggregated_drivers = [aggregate.to_dict() for aggregate in aggregates.values() if abs(aggregate.contribution) >= 0.05]
        aggregated_drivers.sort(key=lambda item: abs(float(item["contribution"])), reverse=True)

        analysis = RiskEngine._format_analysis(cards[0], cards, aggregated_drivers, features)
        recommendations = RiskEngine._recommendations(features, cards, aggregated_drivers)

        risk_payload = {
            "diabetes_risk": diabetes_score,
            "hypertension_risk": hypertension_score,
            "cad_risk": cad_score,
            "cards": cards,
        }

        latest_updated = features.latest_observation_at.isoformat() if features.latest_observation_at else _now_utc().isoformat()

        return {
            "user_id": user_id,
            "status": "ready",
            "risks": risk_payload,
            "drivers": aggregated_drivers[:6],
            "analysis": analysis,
            "recommendations": recommendations,
            "last_updated": latest_updated,
            "confidence": features.confidence,
            "data_points": features.data_points,
            "feature_snapshot": features.to_dict(),
        }
