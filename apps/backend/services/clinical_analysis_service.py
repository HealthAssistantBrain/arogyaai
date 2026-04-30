from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any


class ClinicalAnalysisService:
    SYMPTOM_SYSTEM_MAP = {
        "abdominal pain": "gastrointestinal",
        "breathlessness": "respiratory",
        "chest pain": "cardiovascular",
        "cough": "respiratory",
        "diarrhea": "gastrointestinal",
        "dizziness": "neurologic",
        "fatigue": "metabolic",
        "fever": "infectious",
        "headache": "neurologic",
        "palpitations": "cardiovascular",
        "shortness of breath": "respiratory",
        "vomiting": "gastrointestinal",
        "wheezing": "respiratory",
    }

    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _safe_int(value: Any, default: int | None = None) -> int | None:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
        else:
            items = []

        cleaned: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = ClinicalAnalysisService._clean_text(item)
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned

    @staticmethod
    def _merge_text_lists(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group or []:
                text = ClinicalAnalysisService._clean_text(item)
                key = text.lower()
                if not text or key in seen:
                    continue
                seen.add(key)
                merged.append(text)
        return merged

    @staticmethod
    def _match_symptom(symptoms: list[str], keyword: str) -> bool:
        normalized = keyword.lower()
        return any(normalized in item.lower() for item in symptoms)

    @staticmethod
    def _feature_flag(feature_payload: dict[str, Any], *keys: str, threshold: float) -> bool:
        for key in keys:
            value = feature_payload.get(key)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric >= threshold:
                return True
        return False

    @staticmethod
    def _age_phrase(user_age: int | None) -> str:
        if user_age is None or user_age <= 0:
            return "User"
        return f"{user_age}-year-old user"

    @staticmethod
    def summarize(
        *,
        user_age: int | None,
        chief_complaint: str,
        duration: str,
        onset: str,
        associated_symptoms: list[str],
        negative_symptoms: list[str],
    ) -> str:
        subject = ClinicalAnalysisService._age_phrase(user_age)
        complaint_text = chief_complaint or "symptoms"
        sentence = f"{subject} reports {complaint_text}"

        if duration:
            sentence = f"{sentence} for {duration}"
        if onset:
            sentence = f"{sentence} with {onset.lower()} onset"
        if associated_symptoms:
            connector = " and associated" if onset else " with associated"
            sentence = f"{sentence}{connector} {', '.join(associated_symptoms[:3])}"

        sentence = sentence.strip()
        if negative_symptoms:
            negative_clause = " or ".join(negative_symptoms[:3]) if len(negative_symptoms) <= 3 else ", ".join(negative_symptoms[:2]) + f", or {negative_symptoms[2]}"
            sentence = f"{sentence} but no {negative_clause}."
        else:
            sentence = f"{sentence}."

        return sentence.replace("  ", " ").strip()

    @staticmethod
    def analyze_history(
        history_payload: dict[str, Any] | None,
        *,
        feature_payload: dict[str, Any] | None = None,
        user_age: int | None = None,
    ) -> dict[str, Any]:
        payload = history_payload if isinstance(history_payload, dict) else {}
        features = feature_payload if isinstance(feature_payload, dict) else {}

        chief_complaint = ClinicalAnalysisService._clean_text(payload.get("chief_complaint"))
        duration = ClinicalAnalysisService._clean_text(payload.get("duration"))
        onset = ClinicalAnalysisService._clean_text(payload.get("onset"))
        severity = ClinicalAnalysisService._safe_int(payload.get("severity"))
        associated_symptoms = ClinicalAnalysisService._normalize_list(payload.get("associated_symptoms"))
        negative_symptoms = ClinicalAnalysisService._normalize_list(payload.get("negative_symptoms"))
        symptoms = ClinicalAnalysisService._merge_text_lists([chief_complaint] if chief_complaint else [], associated_symptoms)

        system_counts: dict[str, int] = defaultdict(int)
        for symptom in symptoms:
            lowered = symptom.lower()
            for keyword, system in ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.items():
                if keyword in lowered:
                    system_counts[system] += 1

        system_flags = {
            system: count > 0
            for system, count in sorted(system_counts.items(), key=lambda item: item[0])
        }

        has_high_bp = (
            ClinicalAnalysisService._feature_flag(features, "systolic_bp", threshold=140.0)
            or ClinicalAnalysisService._feature_flag(features, "diastolic_bp", threshold=90.0)
        )
        has_high_glucose = (
            ClinicalAnalysisService._feature_flag(features, "glucose", threshold=126.0)
            or ClinicalAnalysisService._feature_flag(features, "hba1c", threshold=6.5)
        )

        condition_scores: dict[str, float] = {}

        def add_condition(label: str, score: float) -> None:
            current = condition_scores.get(label, 0.0)
            condition_scores[label] = round(max(current, score), 3)

        if ClinicalAnalysisService._match_symptom(symptoms, "chest pain"):
            score = 0.45
            if has_high_bp:
                score += 0.22
            if (severity or 0) >= 7:
                score += 0.12
            if ClinicalAnalysisService._match_symptom(symptoms, "breathlessness") or ClinicalAnalysisService._match_symptom(symptoms, "shortness of breath"):
                score += 0.15
            if ClinicalAnalysisService._match_symptom(negative_symptoms, "breathlessness"):
                score -= 0.08
            add_condition("Cardiac risk", score)

        if ClinicalAnalysisService._match_symptom(symptoms, "cough"):
            infection_score = 0.28
            respiratory_score = 0.34
            if ClinicalAnalysisService._match_symptom(symptoms, "fever"):
                infection_score += 0.28
            if ClinicalAnalysisService._match_symptom(negative_symptoms, "fever"):
                infection_score -= 0.2
            if ClinicalAnalysisService._match_symptom(negative_symptoms, "breathlessness"):
                respiratory_score -= 0.1
            add_condition("Respiratory infection", infection_score)
            add_condition("Respiratory irritation", respiratory_score)

        if ClinicalAnalysisService._match_symptom(symptoms, "fatigue"):
            fatigue_score = 0.24
            metabolic_score = 0.26
            if has_high_glucose:
                metabolic_score += 0.34
            if (severity or 0) >= 7:
                fatigue_score += 0.08
            add_condition("Metabolic fatigue", fatigue_score)
            if has_high_glucose:
                add_condition("Possible diabetes pattern", metabolic_score)

        if ClinicalAnalysisService._match_symptom(symptoms, "dizziness") and has_high_bp:
            add_condition("Hypertensive symptom pattern", 0.58)

        if ClinicalAnalysisService._match_symptom(symptoms, "palpitations") and ClinicalAnalysisService._match_symptom(symptoms, "dizziness"):
            add_condition("Rhythm-related symptom pattern", 0.54)

        if ClinicalAnalysisService._match_symptom(symptoms, "fever") and not ClinicalAnalysisService._match_symptom(negative_symptoms, "fever"):
            add_condition("Acute infection", 0.42)

        if ClinicalAnalysisService._match_symptom(symptoms, "breathlessness") and ClinicalAnalysisService._match_symptom(symptoms, "chest pain"):
            add_condition("Cardiopulmonary concern", 0.72)

        negative_history_impact: list[str] = []
        for symptom_name, impact_text in (
            ("cough", "No cough lowers the probability of a primary respiratory process."),
            ("fever", "No fever reduces the likelihood of an acute infectious pattern."),
            ("breathlessness", "No breathlessness lowers immediate cardiopulmonary urgency."),
            ("chest pain", "No chest pain makes acute cardiac ischemia less likely in this symptom set."),
            ("dizziness", "No dizziness reduces concern for vestibular or hemodynamic instability."),
        ):
            if ClinicalAnalysisService._match_symptom(negative_symptoms, symptom_name):
                negative_history_impact.append(impact_text)

        ordered_conditions = [
            label
            for label, score in sorted(condition_scores.items(), key=lambda item: item[1], reverse=True)
            if score > 0.15
        ]
        if not ordered_conditions:
            ordered_conditions = ["Insufficient symptom data for a focused differential"] if symptoms or negative_symptoms else []

        max_score = max(condition_scores.values(), default=0.0)
        urgent_cardiac = ClinicalAnalysisService._match_symptom(symptoms, "chest pain") and (
            has_high_bp or (severity or 0) >= 8
        )

        if urgent_cardiac or max_score >= 0.7:
            risk_level = "high"
            priority = "urgent"
        elif max_score >= 0.4 or (severity or 0) >= 6:
            risk_level = "medium"
            priority = "soon"
        elif symptoms or negative_symptoms:
            risk_level = "low"
            priority = "routine"
        else:
            risk_level = "low"
            priority = "routine"

        recommendations: list[str] = []
        if priority == "urgent":
            recommendations.append("Prompt in-person clinical evaluation is advisable, especially if symptoms persist or worsen.")
        elif priority == "soon":
            recommendations.append("Arrange a clinical review soon and monitor for progression, new fever, breathlessness, or persistent pain.")
        else:
            recommendations.append("Track symptom progression and document triggers, duration, and response to treatment.")

        if chief_complaint:
            recommendations.append("Carry forward this structured symptom history during the next consultation.")
        if symptoms and not features:
            recommendations.append("Correlate symptoms with vitals, glucose, or recent reports when available to refine the differential.")

        summary = ClinicalAnalysisService.summarize(
            user_age=user_age,
            chief_complaint=chief_complaint,
            duration=duration,
            onset=onset,
            associated_symptoms=associated_symptoms,
            negative_symptoms=negative_symptoms,
        )

        return {
            "summary": summary,
            "symptoms": symptoms,
            "possible_conditions": ordered_conditions[:4],
            "risk_level": risk_level,
            "priority": priority,
            "recommendations": recommendations[:3],
            "negative_history_impact": negative_history_impact,
            "system_flags": system_flags,
            "ml_features": {
                "symptom_count": len(symptoms),
                "severity_score": severity or 0,
                "negative_symptom_count": len(negative_symptoms),
                "system_flags": system_flags,
            },
            "rag_context": {
                "summary": summary,
                "possible_conditions": ordered_conditions[:4],
                "negative_history": negative_symptoms,
                "systems": [system for system, enabled in system_flags.items() if enabled],
            },
        }

    @staticmethod
    def age_from_profile(profile: Any) -> int | None:
        if profile is None:
            return None

        try:
            age_value = getattr(profile, "age", None)
            if age_value is not None:
                age_numeric = int(age_value)
                if age_numeric > 0:
                    return age_numeric
        except (TypeError, ValueError):
            pass

        dob = getattr(profile, "date_of_birth", None)
        if not isinstance(dob, date):
            return None

        today = date.today()
        years = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            years -= 1
        return max(years, 0)
