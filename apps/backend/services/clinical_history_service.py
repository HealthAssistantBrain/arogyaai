from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import ClinicalHistory, User
from pipelines.storage_pipeline.service import StoragePipelineService
from services.clinical_analysis_service import ClinicalAnalysisService


class ClinicalHistoryService:
    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        return ClinicalAnalysisService._normalize_list(value)

    @staticmethod
    def _normalize_duration(value: Any, unit: Any) -> str | None:
        if value in (None, ""):
            return None

        duration_value = None
        try:
            if value not in (None, ""):
                duration_value = int(value)
        except (TypeError, ValueError):
            duration_value = None

        normalized_unit = ClinicalHistoryService._clean_text(unit).lower()
        if normalized_unit.endswith("s"):
            singular_unit = normalized_unit[:-1]
        else:
            singular_unit = normalized_unit

        if normalized_unit and singular_unit not in {"hour", "day", "week"}:
            normalized_unit = ""
            singular_unit = ""

        if duration_value is not None and singular_unit:
            suffix = singular_unit if duration_value == 1 else f"{singular_unit}s"
            return f"{duration_value} {suffix}"
        if duration_value is not None:
            return str(duration_value)
        if normalized_unit:
            return normalized_unit
        return None

    @staticmethod
    def _past_history(previous_episodes: Any, treatment_taken: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if previous_episodes is not None:
            payload["previous_episodes"] = bool(previous_episodes)
        treatment_text = ClinicalHistoryService._clean_text(treatment_taken)
        if treatment_text:
            payload["treatment_taken"] = treatment_text
        return payload

    @staticmethod
    def _normalized_record_payload(payload: Any) -> dict[str, Any]:
        request = payload.model_dump(exclude_none=False) if hasattr(payload, "model_dump") else dict(payload or {})
        return {
            "chief_complaint": ClinicalHistoryService._clean_text(request.get("chief_complaint")) or None,
            "duration": ClinicalHistoryService._normalize_duration(request.get("duration_value"), request.get("duration_unit")),
            "onset": ClinicalHistoryService._clean_text(request.get("onset")) or None,
            "severity": request.get("severity"),
            "associated_symptoms": ClinicalHistoryService._normalize_list(
                request.get("associated_symptoms", request.get("symptoms"))
            ),
            "negative_symptoms": ClinicalHistoryService._normalize_list(request.get("negative_symptoms")),
            "aggravating_factors": ClinicalHistoryService._clean_text(request.get("aggravating_factors")) or None,
            "relieving_factors": ClinicalHistoryService._clean_text(request.get("relieving_factors")) or None,
            "past_history": ClinicalHistoryService._past_history(
                request.get("previous_episodes"),
                request.get("treatment_taken"),
            ),
        }

    @staticmethod
    def _has_structured_payload(payload: dict[str, Any]) -> bool:
        return any(
            [
                payload.get("chief_complaint"),
                payload.get("duration"),
                payload.get("onset"),
                payload.get("associated_symptoms"),
                payload.get("negative_symptoms"),
                payload.get("aggravating_factors"),
                payload.get("relieving_factors"),
                payload.get("past_history"),
            ]
        )

    @staticmethod
    def _user_age(user: User) -> int | None:
        return ClinicalAnalysisService.age_from_profile(getattr(user, "user_profile", None))

    @staticmethod
    def _feature_payload(db: Session, user: User) -> dict[str, Any]:
        snapshot = StoragePipelineService.latest_feature_snapshot(db, user)
        if snapshot and isinstance(getattr(snapshot, "feature_payload", None), dict):
            return dict(snapshot.feature_payload)
        return {}

    @staticmethod
    def _raw_payload(record: ClinicalHistory) -> dict[str, Any]:
        past_history = record.past_history if isinstance(record.past_history, dict) else {}
        return {
            "id": str(record.id),
            "chief_complaint": ClinicalHistoryService._clean_text(record.chief_complaint),
            "duration": ClinicalHistoryService._clean_text(record.duration),
            "onset": ClinicalHistoryService._clean_text(record.onset),
            "severity": record.severity,
            "associated_symptoms": ClinicalHistoryService._normalize_list(record.associated_symptoms),
            "negative_symptoms": ClinicalHistoryService._normalize_list(record.negative_symptoms),
            "aggravating_factors": ClinicalHistoryService._clean_text(record.aggravating_factors),
            "relieving_factors": ClinicalHistoryService._clean_text(record.relieving_factors),
            "past_history": past_history,
            "previous_episodes": past_history.get("previous_episodes"),
            "treatment_taken": ClinicalHistoryService._clean_text(past_history.get("treatment_taken")),
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    @staticmethod
    def serialize(
        record: ClinicalHistory,
        *,
        feature_payload: dict[str, Any] | None = None,
        user_age: int | None = None,
    ) -> dict[str, Any]:
        raw = ClinicalHistoryService._raw_payload(record)
        analysis = ClinicalAnalysisService.analyze_history(
            raw,
            feature_payload=feature_payload,
            user_age=user_age,
        )
        payload = {
            **raw,
            "analysis": analysis,
        }
        payload["timeline_event"] = ClinicalHistoryService.build_timeline_event(record, analysis=analysis)
        return payload

    @staticmethod
    def build_timeline_event(
        record: ClinicalHistory,
        *,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_analysis = analysis or ClinicalAnalysisService.analyze_history(ClinicalHistoryService._raw_payload(record))
        complaint = ClinicalHistoryService._clean_text(record.chief_complaint)
        associated = ClinicalHistoryService._normalize_list(record.associated_symptoms)
        negative = ClinicalHistoryService._normalize_list(record.negative_symptoms)
        description_parts: list[str] = []
        if complaint:
            description_parts.append(f"Complaint: {complaint}.")
        if associated:
            description_parts.append(f"Associated symptoms: {', '.join(associated[:4])}.")
        if negative:
            description_parts.append(f"Negative history: no {', '.join(negative[:4])}.")
        description = " ".join(description_parts).strip() or resolved_analysis.get("summary") or "Structured clinical history added."

        metrics = []
        if record.severity is not None:
            metrics.append({"label": "Severity", "value": f"{record.severity}/10"})
        metrics.append({"label": "Risk", "value": str(resolved_analysis.get("risk_level") or "low").upper()})
        metrics.append({"label": "Priority", "value": str(resolved_analysis.get("priority") or "routine").upper()})

        systems = [system.replace("_", " ").title() for system, enabled in (resolved_analysis.get("system_flags") or {}).items() if enabled]
        if systems:
            metrics.append({"label": "Systems", "value": ", ".join(systems[:2])})

        return {
            "id": f"clinical_history_{record.id}",
            "type": "Clinical History",
            "source": "patient intake",
            "category": "symptom",
            "title": complaint or "Clinical history added",
            "description": description,
            "timestamp": record.created_at.isoformat() if record.created_at else None,
            "event_date": record.created_at.isoformat() if record.created_at else None,
            "metrics": metrics,
            "severity": f"{record.severity}/10" if record.severity is not None else None,
            "insights": resolved_analysis.get("summary"),
            "possible_conditions": resolved_analysis.get("possible_conditions") or [],
            "recommendations": resolved_analysis.get("recommendations") or [],
            "metadata": {
                "chief_complaint": complaint or None,
                "severity": record.severity,
                "risk_level": resolved_analysis.get("risk_level"),
                "priority": resolved_analysis.get("priority"),
                "associated_symptoms": associated,
                "negative_symptoms": negative,
            },
        }

    @staticmethod
    def create_history(
        db: Session,
        current_user: User,
        payload: Any,
    ) -> dict[str, Any]:
        normalized = ClinicalHistoryService._normalized_record_payload(payload)
        if not ClinicalHistoryService._has_structured_payload(normalized):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one structured clinical history field is required.",
            )

        record = ClinicalHistory(
            user_id=current_user.id,
            **normalized,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ClinicalHistoryService.serialize(
            record,
            feature_payload=ClinicalHistoryService._feature_payload(db, current_user),
            user_age=ClinicalHistoryService._user_age(current_user),
        )

    @staticmethod
    def upsert_initial_snapshot(
        db: Session,
        current_user: User,
        payload: Any,
    ) -> dict[str, Any] | None:
        normalized = ClinicalHistoryService._normalized_record_payload(payload)
        latest_record = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == current_user.id)
            .order_by(ClinicalHistory.created_at.desc())
            .first()
        )

        if not ClinicalHistoryService._has_structured_payload(normalized):
            if latest_record is None:
                return None
            latest_record.chief_complaint = None
            latest_record.duration = None
            latest_record.onset = None
            latest_record.severity = None
            latest_record.associated_symptoms = []
            latest_record.negative_symptoms = []
            latest_record.aggravating_factors = None
            latest_record.relieving_factors = None
            latest_record.past_history = {}
            db.commit()
            db.refresh(latest_record)
            return None

        record = latest_record or ClinicalHistory(user_id=current_user.id)
        if latest_record is None:
            db.add(record)

        record.chief_complaint = normalized["chief_complaint"]
        record.duration = normalized["duration"]
        record.onset = normalized["onset"]
        record.severity = normalized["severity"]
        record.associated_symptoms = normalized["associated_symptoms"]
        record.negative_symptoms = normalized["negative_symptoms"]
        record.aggravating_factors = normalized["aggravating_factors"]
        record.relieving_factors = normalized["relieving_factors"]
        record.past_history = normalized["past_history"]

        db.commit()
        db.refresh(record)
        return ClinicalHistoryService.serialize(
            record,
            feature_payload=ClinicalHistoryService._feature_payload(db, current_user),
            user_age=ClinicalHistoryService._user_age(current_user),
        )

    @staticmethod
    def latest_history_analysis(
        db: Session,
        user: User,
        *,
        feature_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        record = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user.id)
            .order_by(ClinicalHistory.created_at.desc())
            .first()
        )
        if record is None or not isinstance(record, ClinicalHistory):
            return None
        return ClinicalHistoryService.serialize(
            record,
            feature_payload=feature_payload,
            user_age=ClinicalHistoryService._user_age(user),
        )

    @staticmethod
    def list_histories(
        db: Session,
        user: User,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        feature_payload = ClinicalHistoryService._feature_payload(db, user)
        user_age = ClinicalHistoryService._user_age(user)
        rows = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user.id)
            .order_by(ClinicalHistory.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [
            ClinicalHistoryService.serialize(row, feature_payload=feature_payload, user_age=user_age)
            for row in rows
        ]
