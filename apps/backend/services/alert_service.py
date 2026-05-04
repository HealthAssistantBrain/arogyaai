from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import (
    Alert,
    AlertTypeEnum,
    RiskScore,
    SeverityEnum,
    User,
    UserVital,
    UserVitalTypeEnum,
)
from pipelines.anomaly_pipeline.service import AnomalyPipelineService
from services.event_service import emit_event

ALERT_DEDUPE_WINDOW = timedelta(hours=12)
ACTIVE_ALERT_LIMIT = 20


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_user_id(user_id: Any) -> uuid.UUID | None:
    try:
        return user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None


def _load_user(db: Session, user_id: uuid.UUID) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id, User.is_deleted == False)
        .first()
    )


def _latest_user_vital(db: Session, user_id: uuid.UUID, vital_type: UserVitalTypeEnum) -> UserVital | None:
    return (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user_id,
            UserVital.vital_type == vital_type,
        )
        .order_by(UserVital.timestamp.desc())
        .first()
    )


def _latest_risk_score(db: Session, user_id: uuid.UUID) -> RiskScore | None:
    return (
        db.query(RiskScore)
        .filter(RiskScore.user_id == user_id)
        .order_by(RiskScore.calculated_at.desc(), RiskScore.created_at.desc())
        .first()
    )


def _sleep_minutes(vital: UserVital | None) -> float | None:
    if vital is None or vital.value is None:
        return None

    unit = str(vital.unit or "").strip().lower()
    value = float(vital.value)

    if unit in {"hour", "hours", "hr", "hrs"}:
        return value * 60.0
    return value


def _normalized_risk_score(record: RiskScore | None) -> float | None:
    if record is None or record.overall_score is None:
        return None

    score = float(record.overall_score)
    if score > 1.0:
        if score <= 100.0:
            return score / 100.0
        return score
    return score


def _find_recent_duplicate_alert(
    db: Session,
    *,
    user_id: uuid.UUID,
    alert_type: AlertTypeEnum,
    severity: SeverityEnum,
    title: str,
) -> Alert | None:
    threshold = _now_utc() - ALERT_DEDUPE_WINDOW
    return (
        db.query(Alert)
        .filter(
            Alert.user_id == user_id,
            Alert.alert_type == alert_type,
            Alert.severity == severity,
            Alert.title == title,
            Alert.created_at >= threshold,
        )
        .order_by(Alert.created_at.desc())
        .first()
    )


def _store_alert(
    db: Session,
    *,
    user_id: uuid.UUID,
    alert_type: AlertTypeEnum,
    severity: SeverityEnum,
    title: str,
    message: str,
) -> Alert | None:
    duplicate = _find_recent_duplicate_alert(
        db,
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
    )
    if duplicate is not None:
        return None

    alert = Alert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(alert)
    return alert


def _list_active_alert_models(
    db: Session,
    user_id: uuid.UUID,
    *,
    limit: int = ACTIVE_ALERT_LIMIT,
) -> list[Alert]:
    return (
        db.query(Alert)
        .filter(
            Alert.user_id == user_id,
            Alert.is_read.is_(False),
        )
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )


def _ui_severity(value: SeverityEnum | str | None) -> str:
    raw = value.value if isinstance(value, SeverityEnum) else str(value or "").upper()
    if raw == SeverityEnum.CRITICAL.value:
        return "critical"
    if raw == SeverityEnum.WARNING.value:
        return "warning"
    return "info"


def _severity_label(value: SeverityEnum | str | None) -> str:
    raw = value.value if isinstance(value, SeverityEnum) else str(value or "").upper()
    if raw == SeverityEnum.CRITICAL.value:
        return "HIGH"
    if raw == SeverityEnum.WARNING.value:
        return "MEDIUM"
    return "INFO"


def _serialize_alert(alert: Alert) -> dict[str, Any]:
    return {
        "id": str(alert.id),
        "anomaly_id": str(alert.id) if alert.alert_type == AlertTypeEnum.VITAL_ANOMALY else None,
        "user_id": str(alert.user_id),
        "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
        "severity": _ui_severity(alert.severity),
        "severity_label": _severity_label(alert.severity),
        "title": alert.title,
        "message": alert.message,
        "is_read": bool(alert.is_read),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def generate_health_alerts(user_id: Any, db: Session | None = None) -> list[dict[str, Any]]:
    managed_session = db is None
    session = db or SessionLocal()

    try:
        user_uuid = _coerce_user_id(user_id)
        if user_uuid is None:
            return []

        user = _load_user(session, user_uuid)
        if user is None:
            return []

        created_any = False
        created_alerts: list[Alert] = []

        latest_heart_rate = _latest_user_vital(session, user_uuid, UserVitalTypeEnum.HEART_RATE)
        if latest_heart_rate is not None and latest_heart_rate.value is not None and float(latest_heart_rate.value) > 100.0:
            created_alert = _store_alert(
                session,
                user_id=user_uuid,
                alert_type=AlertTypeEnum.VITAL_ANOMALY,
                severity=SeverityEnum.CRITICAL,
                title="High heart rate detected",
                message=f"Latest heart rate was {float(latest_heart_rate.value):.0f} bpm, above the 100 bpm threshold.",
            )
            if created_alert is not None:
                created_alerts.append(created_alert)
                created_any = True

        latest_sleep = _latest_user_vital(session, user_uuid, UserVitalTypeEnum.SLEEP)
        sleep_minutes = _sleep_minutes(latest_sleep)
        if sleep_minutes is not None and sleep_minutes < 300.0:
            created_alert = _store_alert(
                session,
                user_id=user_uuid,
                alert_type=AlertTypeEnum.VITAL_ANOMALY,
                severity=SeverityEnum.WARNING,
                title="Low sleep duration detected",
                message=f"Latest sleep duration was {sleep_minutes:.0f} minutes, below the 300 minute threshold.",
            )
            if created_alert is not None:
                created_alerts.append(created_alert)
                created_any = True

        latest_risk = _latest_risk_score(session, user_uuid)
        normalized_risk_score = _normalized_risk_score(latest_risk)
        if normalized_risk_score is not None and normalized_risk_score > 0.7:
            created_alert = _store_alert(
                session,
                user_id=user_uuid,
                alert_type=AlertTypeEnum.VITAL_ANOMALY,
                severity=SeverityEnum.CRITICAL,
                title="Elevated health risk score detected",
                message=f"Latest risk score was {normalized_risk_score:.2f}, above the 0.70 threshold.",
            )
            if created_alert is not None:
                created_alerts.append(created_alert)
                created_any = True

        try:
            anomaly_signals = AnomalyPipelineService.detect_recent_vital_anomalies(session, user)
        except Exception:
            anomaly_signals = []

        for signal in anomaly_signals:
            severity = (
                SeverityEnum.CRITICAL
                if str(signal.get("severity") or "").lower() == "critical"
                else SeverityEnum.WARNING
            )
            created_alert = _store_alert(
                session,
                user_id=user_uuid,
                alert_type=AlertTypeEnum.VITAL_ANOMALY,
                severity=severity,
                title=str(signal.get("title") or "Wearable anomaly detected"),
                message=str(signal.get("message") or "A recent wearable metric differs from your usual baseline."),
            )
            if created_alert is not None:
                created_alerts.append(created_alert)
                created_any = True

        if created_any:
            session.commit()
            for alert in created_alerts:
                try:
                    emit_event(
                        "HEALTH_ALERT_GENERATED",
                        user_uuid,
                        {
                            "title": alert.title,
                            "description": alert.message,
                            "severity": _ui_severity(alert.severity),
                            "alert_id": str(alert.id),
                        },
                    )
                except Exception:
                    pass

        alerts = _list_active_alert_models(session, user_uuid)
        return [_serialize_alert(alert) for alert in alerts]
    finally:
        if managed_session:
            session.close()


async def get_active_alerts(user: User, db: Session) -> dict[str, Any]:
    alerts = generate_health_alerts(user.id, db)
    return {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": {"alerts": alerts},
    }
