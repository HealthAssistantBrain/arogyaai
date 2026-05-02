from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from models import (
    Alert,
    Notification,
    NotificationSeverityEnum,
    NotificationTypeEnum,
    PriorityEnum,
    RecCategoryEnum,
    Recommendation,
    RiskScore,
    ShapValueRecord,
    User,
    UserProfile,
    UserVital,
    UserVitalTypeEnum,
)
from models.user import ROLE_DOCTOR
from pipelines.storage_pipeline.service import StoragePipelineService
from services.alert_service import generate_health_alerts
from services.notification_service import NotificationService
from services.prediction_explanation_service import PredictionExplanationService
from services.timeline_service import build_timeline_events


TRIAGE_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MODERATE": 2,
    "LOW": 3,
    "UNKNOWN": 4,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _risk_percent(value: Any) -> float | None:
    score = _safe_float(value)
    if score is None:
        return None
    if 0 <= score <= 1:
        return round(score * 100, 1)
    return round(score, 1)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def _severity_value(value: Any) -> str:
    return _enum_value(value).lower()


def _coerce_uuid(value: Any, label: str = "id") -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label}",
        ) from exc


def _patient_name(user: User, profile: UserProfile | None = None) -> str:
    profile_name = getattr(profile, "full_name", None)
    return profile_name or user.full_name or user.email.split("@", 1)[0] or "Patient"


def _event_time(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return parsed.timestamp()


class DoctorService:
    @staticmethod
    def _patient_query(db: Session):
        return (
            db.query(User)
            .filter(
                User.is_deleted == False,
                or_(User.role.is_(None), User.role != ROLE_DOCTOR),
            )
        )

    @staticmethod
    def _get_patient(db: Session, patient_id: Any) -> User:
        patient_uuid = _coerce_uuid(patient_id, "patient id")
        patient = (
            DoctorService._patient_query(db)
            .filter(User.id == patient_uuid)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        return patient

    @staticmethod
    def _profile(db: Session, user: User) -> UserProfile | None:
        return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    @staticmethod
    def _latest_vital(db: Session, user: User, vital_type: UserVitalTypeEnum) -> UserVital | None:
        return (
            db.query(UserVital)
            .filter(UserVital.user_id == user.id, UserVital.vital_type == vital_type)
            .order_by(UserVital.timestamp.desc())
            .first()
        )

    @staticmethod
    def _recent_vitals(
        db: Session,
        user: User,
        vital_type: UserVitalTypeEnum,
        *,
        limit: int = 18,
    ) -> list[dict[str, Any]]:
        rows = (
            db.query(UserVital)
            .filter(UserVital.user_id == user.id, UserVital.vital_type == vital_type)
            .order_by(UserVital.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "type": _enum_value(row.vital_type),
                "value": row.value,
                "unit": row.unit,
                "timestamp": _iso(row.timestamp),
                "source": _enum_value(row.source),
            }
            for row in reversed(rows)
        ]

    @staticmethod
    def _latest_activity_at(db: Session, user: User, risk_score: RiskScore | None = None) -> str | None:
        candidates: list[datetime] = []

        latest_vital = (
            db.query(UserVital)
            .filter(UserVital.user_id == user.id)
            .order_by(UserVital.timestamp.desc())
            .first()
        )
        if latest_vital and latest_vital.timestamp:
            candidates.append(latest_vital.timestamp)
        if risk_score and risk_score.calculated_at:
            candidates.append(risk_score.calculated_at)

        latest_alert = (
            db.query(Alert)
            .filter(Alert.user_id == user.id)
            .order_by(Alert.created_at.desc())
            .first()
        )
        if latest_alert and latest_alert.created_at:
            candidates.append(latest_alert.created_at)

        latest_notification = (
            db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .first()
        )
        if latest_notification and latest_notification.created_at:
            candidates.append(latest_notification.created_at)

        if user.updated_at:
            candidates.append(user.updated_at)
        if user.created_at:
            candidates.append(user.created_at)

        if not candidates:
            return None
        return max(candidates).isoformat()

    @staticmethod
    def _active_alert_counts(db: Session, user: User) -> dict[str, Any]:
        generate_health_alerts(user.id, db)

        alerts = (
            db.query(Alert)
            .filter(Alert.user_id == user.id, Alert.is_read.is_(False))
            .order_by(Alert.created_at.desc())
            .limit(20)
            .all()
        )
        health_notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT,
                Notification.is_read.is_(False),
            )
            .order_by(Notification.created_at.desc())
            .limit(20)
            .all()
        )
        critical_count = sum(1 for item in alerts if _severity_value(item.severity) == "critical")
        critical_count += sum(1 for item in health_notifications if _severity_value(item.severity) == "critical")
        active_count = len(alerts) + len(health_notifications)

        if critical_count:
            label = "critical"
        elif active_count:
            label = "active"
        else:
            label = "clear"

        return {
            "status": label,
            "active_count": active_count,
            "critical_count": critical_count,
        }

    @staticmethod
    def _patient_summary(db: Session, user: User) -> dict[str, Any]:
        profile = DoctorService._profile(db, user)
        risk = StoragePipelineService.latest_risk_score(db, user)
        risk_level = (
            _enum_value(risk.risk_level).upper()
            if risk is not None and risk.risk_level is not None
            else "UNKNOWN"
        )
        alert_status = DoctorService._active_alert_counts(db, user)
        last_activity = DoctorService._latest_activity_at(db, user, risk)

        return {
            "id": str(user.id),
            "patient_id": str(user.id),
            "name": _patient_name(user, profile),
            "email": user.email,
            "risk_score": _risk_percent(risk.overall_score if risk else None),
            "triage_level": risk_level,
            "last_activity": last_activity,
            "alert_status": alert_status["status"],
            "active_alerts": alert_status["active_count"],
            "critical_alerts": alert_status["critical_count"],
            "prediction_id": str(risk.id) if risk else None,
        }

    @staticmethod
    def list_patients(db: Session, doctor: User) -> dict[str, Any]:
        patients = DoctorService._patient_query(db).order_by(User.created_at.desc()).all()
        summaries = [DoctorService._patient_summary(db, patient) for patient in patients]
        summaries.sort(
            key=lambda item: (
                TRIAGE_ORDER.get(item.get("triage_level") or "UNKNOWN", 4),
                -int(item.get("critical_alerts") or 0),
                -_event_time(item.get("last_activity")),
            )
        )

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "patients": summaries,
                "total_count": len(summaries),
                "doctor": {
                    "id": str(doctor.id),
                    "name": doctor.full_name or doctor.email,
                    "role": doctor.role,
                },
            },
            "last_updated": _now_iso(),
        }

    @staticmethod
    def _serialize_latest_vital(row: UserVital | None, default_unit: str) -> dict[str, Any]:
        if row is None:
            return {
                "value": None,
                "unit": default_unit,
                "timestamp": None,
                "source": None,
                "status": "missing",
            }
        return {
            "id": str(row.id),
            "value": row.value,
            "unit": row.unit or default_unit,
            "timestamp": _iso(row.timestamp),
            "source": _enum_value(row.source),
            "status": "ready",
        }

    @staticmethod
    def _vitals_panel(db: Session, patient: User) -> dict[str, Any]:
        heart_rate = DoctorService._latest_vital(db, patient, UserVitalTypeEnum.HEART_RATE)
        sleep = DoctorService._latest_vital(db, patient, UserVitalTypeEnum.SLEEP)
        steps = DoctorService._latest_vital(db, patient, UserVitalTypeEnum.STEPS)
        latest_feature = StoragePipelineService.latest_feature_snapshot(db, patient)
        feature_payload = latest_feature.feature_payload if latest_feature and isinstance(latest_feature.feature_payload, dict) else {}

        return {
            "heart_rate": DoctorService._serialize_latest_vital(heart_rate, "bpm"),
            "sleep": DoctorService._serialize_latest_vital(sleep, "minutes"),
            "activity": DoctorService._serialize_latest_vital(steps, "steps"),
            "feature_snapshot": {
                "id": str(latest_feature.id) if latest_feature else None,
                "hr_mean_7d": _safe_float(latest_feature.hr_mean_7d if latest_feature else None),
                "steps_avg_7d": _safe_float(latest_feature.steps_avg_7d if latest_feature else None),
                "sleep_efficiency": _safe_float(latest_feature.sleep_efficiency if latest_feature else None),
                "calculated_at": _iso(latest_feature.calculated_at) if latest_feature else None,
                "payload": feature_payload,
            },
            "history": {
                "heart_rate": DoctorService._recent_vitals(db, patient, UserVitalTypeEnum.HEART_RATE),
                "sleep": DoctorService._recent_vitals(db, patient, UserVitalTypeEnum.SLEEP),
                "activity": DoctorService._recent_vitals(db, patient, UserVitalTypeEnum.STEPS),
            },
        }

    @staticmethod
    def _prediction_panel(db: Session, patient: User, risk: RiskScore | None) -> dict[str, Any]:
        if risk is None:
            return {
                "latest": None,
                "insights": None,
                "recommendations": [],
                "status": "empty",
            }

        payload = risk.risk_payload if isinstance(risk.risk_payload, dict) else {}
        health_insights = StoragePipelineService.fetch_health_insights(db, patient)
        return {
            "latest": {
                "prediction_id": str(risk.id),
                "risk_score": _risk_percent(risk.overall_score),
                "raw_score": _safe_float(risk.overall_score),
                "risk_level": _enum_value(risk.risk_level).upper(),
                "confidence": _risk_percent(risk.confidence_score),
                "health_score": _risk_percent(risk.health_score),
                "model_version": risk.model_version,
                "prediction_source": risk.prediction_source,
                "prediction_status": risk.prediction_status,
                "calculated_at": _iso(risk.calculated_at),
                "created_at": _iso(risk.created_at),
            },
            "insights": health_insights,
            "risks": payload.get("risks") if isinstance(payload.get("risks"), dict) else {},
            "drivers": payload.get("drivers") if isinstance(payload.get("drivers"), list) else [],
            "recommendations": payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else [],
            "analysis": payload.get("analysis"),
            "status": "ready",
        }

    @staticmethod
    def _shap_panel(db: Session, risk: RiskScore | None) -> list[dict[str, Any]]:
        if risk is None:
            return []

        rows = StoragePipelineService.latest_shap_values(db, risk.id)
        serialized = [
            {
                "id": str(row.id),
                "feature_name": row.feature_name,
                "shap_value": float(row.shap_value),
                "abs_shap_value": float(row.abs_shap_value),
                "direction": row.direction,
                "explanation": row.explanation,
                "source_type": row.source_type,
                "calculated_at": _iso(row.calculated_at),
                "payload": row.shap_payload if isinstance(row.shap_payload, dict) else {},
            }
            for row in rows
        ]
        serialized.sort(key=lambda item: float(item.get("abs_shap_value") or 0.0), reverse=True)

        if serialized:
            return serialized[:8]

        payload = risk.risk_payload if isinstance(risk.risk_payload, dict) else {}
        fallback_drivers = payload.get("drivers") if isinstance(payload.get("drivers"), list) else []
        return [
            {
                "id": f"driver_{index}",
                "feature_name": str(item.get("feature_name") or item.get("feature") or item.get("key") or "driver"),
                "shap_value": _safe_float(item.get("shap_value") or item.get("value") or item.get("contribution"), 0.0),
                "abs_shap_value": abs(_safe_float(item.get("shap_value") or item.get("value") or item.get("contribution"), 0.0) or 0.0),
                "direction": str(item.get("direction") or "unknown"),
                "explanation": item.get("explanation") or item.get("detail"),
                "source_type": "risk_payload",
                "calculated_at": _iso(risk.calculated_at),
                "payload": item,
            }
            for index, item in enumerate(fallback_drivers[:8])
            if isinstance(item, dict)
        ]

    @staticmethod
    def _serialize_alert_model(alert: Alert, patient: User, patient_name: str) -> dict[str, Any]:
        severity = _severity_value(alert.severity)
        return {
            "id": f"alert_{alert.id}",
            "record_id": str(alert.id),
            "patient_id": str(patient.id),
            "patient_name": patient_name,
            "source": "alert",
            "type": _enum_value(alert.alert_type),
            "severity": severity,
            "title": alert.title,
            "message": alert.message,
            "created_at": _iso(alert.created_at),
            "is_read": bool(alert.is_read),
            "emergency": severity == "critical" or "emergency" in (alert.title or "").lower(),
        }

    @staticmethod
    def _serialize_notification_model(notification: Notification, patient: User, patient_name: str) -> dict[str, Any]:
        metadata = notification.event_metadata if isinstance(notification.event_metadata, dict) else {}
        severity = _severity_value(notification.severity)
        return {
            "id": f"notification_{notification.id}",
            "record_id": str(notification.id),
            "patient_id": str(patient.id),
            "patient_name": patient_name,
            "source": "notification",
            "type": _enum_value(notification.notification_type),
            "severity": severity,
            "title": notification.title,
            "message": notification.description,
            "created_at": _iso(notification.created_at),
            "is_read": bool(notification.is_read),
            "metadata": metadata,
            "emergency": bool(metadata.get("emergency")) or severity == "critical",
        }

    @staticmethod
    def _patient_alerts(db: Session, patient: User, *, include_read: bool = False) -> list[dict[str, Any]]:
        profile = DoctorService._profile(db, patient)
        patient_name = _patient_name(patient, profile)
        generate_health_alerts(patient.id, db)

        alert_query = db.query(Alert).filter(Alert.user_id == patient.id)
        notification_query = db.query(Notification).filter(
            Notification.user_id == patient.id,
            Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT,
        )
        if not include_read:
            alert_query = alert_query.filter(Alert.is_read.is_(False))
            notification_query = notification_query.filter(Notification.is_read.is_(False))

        alerts = [
            DoctorService._serialize_alert_model(row, patient, patient_name)
            for row in alert_query.order_by(Alert.created_at.desc()).limit(30).all()
        ]
        notifications = [
            DoctorService._serialize_notification_model(row, patient, patient_name)
            for row in notification_query.order_by(Notification.created_at.desc()).limit(30).all()
        ]
        merged = alerts + notifications
        merged.sort(
            key=lambda item: (
                0 if item.get("emergency") else 1,
                0 if item.get("severity") == "critical" else 1,
                -_event_time(item.get("created_at")),
            )
        )
        return merged

    @staticmethod
    async def get_patient_detail(db: Session, doctor: User, patient_id: Any) -> dict[str, Any]:
        patient = DoctorService._get_patient(db, patient_id)
        profile = DoctorService._profile(db, patient)
        risk = StoragePipelineService.latest_risk_score(db, patient)
        rag_explanation = None
        rag_status = "empty"
        rag_error = None

        if risk is not None:
            explanation_response = await PredictionExplanationService.get_prediction_explanation(
                db,
                patient,
                prediction_id=str(risk.id),
            )
            rag_explanation = explanation_response.get("data") if isinstance(explanation_response, dict) else None
            rag_status = explanation_response.get("status", "fallback") if isinstance(explanation_response, dict) else "fallback"
            rag_error = explanation_response.get("error") if isinstance(explanation_response, dict) else None

        summary = DoctorService._patient_summary(db, patient)
        timeline = build_timeline_events(db, patient.id, include_vitals=True, limit_per_type=25)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "patient": {
                    **summary,
                    "profile": {
                        "age": getattr(profile, "age", None),
                        "gender": getattr(profile, "gender", None),
                        "city": getattr(profile, "city", None),
                        "blood_group": getattr(profile, "blood_group", None),
                    },
                },
                "vitals": DoctorService._vitals_panel(db, patient),
                "ml_predictions": DoctorService._prediction_panel(db, patient, risk),
                "shap_insights": DoctorService._shap_panel(db, risk),
                "rag_explanation": {
                    "status": rag_status,
                    "error": rag_error,
                    "data": rag_explanation,
                },
                "alerts": DoctorService._patient_alerts(db, patient),
                "history": timeline,
                "action_state": {
                    "can_mark_reviewed": True,
                    "can_send_recommendation": True,
                    "can_trigger_follow_up": True,
                    "doctor_id": str(doctor.id),
                },
            },
            "last_updated": _now_iso(),
        }

    @staticmethod
    def list_alerts(db: Session, doctor: User, *, limit: int = 80) -> dict[str, Any]:
        patients = DoctorService._patient_query(db).all()
        alerts: list[dict[str, Any]] = []
        for patient in patients:
            alerts.extend(DoctorService._patient_alerts(db, patient))

        alerts.sort(
            key=lambda item: (
                0 if item.get("emergency") else 1,
                0 if item.get("severity") == "critical" else 1,
                -_event_time(item.get("created_at")),
            )
        )
        trimmed = alerts[: max(1, min(limit, 200))]

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "alerts": trimmed,
                "total_count": len(alerts),
                "doctor_id": str(doctor.id),
            },
            "last_updated": _now_iso(),
        }

    @staticmethod
    def mark_patient_reviewed(db: Session, doctor: User, patient_id: Any) -> dict[str, Any]:
        patient = DoctorService._get_patient(db, patient_id)
        alert_count = (
            db.query(Alert)
            .filter(Alert.user_id == patient.id, Alert.is_read.is_(False))
            .update({"is_read": True}, synchronize_session=False)
        )
        notification_count = (
            db.query(Notification)
            .filter(
                Notification.user_id == patient.id,
                Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT,
                Notification.is_read.is_(False),
            )
            .update({"is_read": True}, synchronize_session=False)
        )
        db.commit()

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "patient_id": str(patient.id),
                "reviewed_by": str(doctor.id),
                "alerts_reviewed": int(alert_count or 0),
                "notifications_reviewed": int(notification_count or 0),
            },
            "last_updated": _now_iso(),
        }

    @staticmethod
    def send_recommendation(
        db: Session,
        doctor: User,
        patient_id: Any,
        *,
        message: str,
        priority: str = "medium",
    ) -> dict[str, Any]:
        patient = DoctorService._get_patient(db, patient_id)
        text = str(message or "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recommendation message is required")

        normalized_priority = str(priority or "medium").strip().upper()
        priority_enum = PriorityEnum.__members__.get(normalized_priority, PriorityEnum.MEDIUM)
        severity = NotificationSeverityEnum.WARNING if priority_enum in {PriorityEnum.HIGH, PriorityEnum.URGENT} else NotificationSeverityEnum.INFO
        risk = StoragePipelineService.latest_risk_score(db, patient)
        recommendation_id = None

        if risk is not None:
            recommendation = Recommendation(
                risk_score_id=risk.id,
                category=RecCategoryEnum.CONSULTATION,
                priority=priority_enum,
                recommendation_text=text,
            )
            db.add(recommendation)
            db.commit()
            db.refresh(recommendation)
            recommendation_id = str(recommendation.id)

        notification = NotificationService.create_notification(
            db,
            patient.id,
            NotificationTypeEnum.SYSTEM,
            "Doctor recommendation",
            text,
            severity,
            metadata={
                "doctor_id": str(doctor.id),
                "patient_id": str(patient.id),
                "recommendation_id": recommendation_id,
                "priority": priority_enum.value,
                "source": "doctor_dashboard",
            },
            dispatch=False,
        )

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "patient_id": str(patient.id),
                "recommendation_id": recommendation_id,
                "notification": notification.get("data", {}).get("notification"),
            },
            "last_updated": _now_iso(),
        }

    @staticmethod
    def trigger_follow_up(
        db: Session,
        doctor: User,
        patient_id: Any,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        patient = DoctorService._get_patient(db, patient_id)
        clean_reason = str(reason or "").strip()
        message = clean_reason or "Your clinician requested a follow-up review based on the latest monitoring data."
        notification = NotificationService.create_notification(
            db,
            patient.id,
            NotificationTypeEnum.APPOINTMENT,
            "Follow-up requested",
            message,
            NotificationSeverityEnum.WARNING,
            metadata={
                "doctor_id": str(doctor.id),
                "patient_id": str(patient.id),
                "source": "doctor_dashboard",
                "url": "/notifications",
            },
            dispatch=False,
        )

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "patient_id": str(patient.id),
                "notification": notification.get("data", {}).get("notification"),
            },
            "last_updated": _now_iso(),
        }
