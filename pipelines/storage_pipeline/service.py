"""Persistence helpers shared by the pipeline stack."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import (
    BaselineMetricRecord,
    FeatureSnapshotRecord,
    HealthScoreRecord,
    LabValue,
    PriorityEnum,
    Recommendation,
    RecCategoryEnum,
    RiskLevelEnum,
    RiskScore,
    ShapValueRecord,
    User,
)


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _risk_level_from_score(score: float) -> RiskLevelEnum:
    if score >= 65.0:
        return RiskLevelEnum.CRITICAL
    if score >= 45.0:
        return RiskLevelEnum.HIGH
    if score >= 25.0:
        return RiskLevelEnum.MODERATE
    return RiskLevelEnum.LOW


def _recommendation_category(label: str | None) -> RecCategoryEnum:
    normalized = (label or "").strip().lower()
    if normalized in {"sleep", "recovery"}:
        return RecCategoryEnum.LIFESTYLE
    if normalized in {"activity", "exercise"}:
        return RecCategoryEnum.EXERCISE
    if normalized in {"diet", "metabolic"}:
        return RecCategoryEnum.DIET
    if normalized in {"cardiovascular", "blood_pressure"}:
        return RecCategoryEnum.CONSULTATION
    return RecCategoryEnum.LIFESTYLE


def _recommendation_priority(value: Any) -> PriorityEnum:
    candidate = str(value or "MEDIUM").upper()
    if candidate in PriorityEnum.__members__:
        return PriorityEnum[candidate]
    return PriorityEnum.MEDIUM


class StoragePipelineService:
    """Central DB write/read utility for all pipeline stages."""

    @staticmethod
    def store_feature_snapshot(
        db: Session,
        user: User,
        snapshot: Any,
        *,
        report_id: UUID | str | None = None,
    ) -> FeatureSnapshotRecord:
        record = FeatureSnapshotRecord(
            user_id=user.id,
            report_id=report_id,
            hr_mean_7d=getattr(snapshot, "hr_mean_7d", None),
            steps_avg_7d=getattr(snapshot, "steps_avg_7d", None),
            sleep_efficiency=getattr(snapshot, "sleep_efficiency", None),
            bmi=getattr(snapshot, "bmi", None),
            lifestyle_score=getattr(snapshot, "lifestyle_score", None),
            activity_score=getattr(snapshot, "activity_score", None),
            sleep_score=getattr(snapshot, "sleep_score", None),
            confidence=getattr(snapshot, "confidence", None),
            latest_observation_at=getattr(snapshot, "latest_observation_at", None),
            feature_payload=getattr(snapshot, "to_dict", lambda: {})(),
            source_breakdown=getattr(snapshot, "source_breakdown", None),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def store_baseline_metrics(
        db: Session,
        user: User,
        metrics: Iterable[dict[str, Any]],
    ) -> list[BaselineMetricRecord]:
        persisted: list[BaselineMetricRecord] = []
        for metric in metrics:
            metric_name = str(metric.get("metric_name") or metric.get("name") or "").strip()
            if not metric_name:
                continue

            record = (
                db.query(BaselineMetricRecord)
                .filter(
                    BaselineMetricRecord.user_id == user.id,
                    BaselineMetricRecord.metric_name == metric_name,
                )
                .one_or_none()
            )
            if record is None:
                record = BaselineMetricRecord(user_id=user.id, metric_name=metric_name)
                db.add(record)

            record.mean_7d = metric.get("mean_7d")
            record.mean_30d = metric.get("mean_30d")
            record.std_dev = metric.get("std_dev")
            record.sample_count = int(metric.get("sample_count") or 0)
            record.window_start = metric.get("window_start")
            record.window_end = metric.get("window_end")
            record.metric_payload = metric
            persisted.append(record)

        db.commit()
        for record in persisted:
            db.refresh(record)
        return persisted

    @staticmethod
    def store_lab_values(
        db: Session,
        user: User,
        values: Iterable[dict[str, Any]],
        *,
        report_id: UUID | str | None = None,
    ) -> list[LabValue]:
        persisted: list[LabValue] = []
        for item in values:
            name = str(item.get("name") or item.get("biomarker_name") or "").strip()
            if not name:
                continue

            record = (
                db.query(LabValue)
                .filter(
                    LabValue.user_id == user.id,
                    LabValue.report_id == report_id,
                    LabValue.biomarker_name == name,
                )
                .one_or_none()
            )
            if record is None:
                record = LabValue(user_id=user.id, report_id=report_id, biomarker_name=name)
                db.add(record)

            record.value = float(item.get("value") or item.get("raw_value") or 0.0)
            record.unit = item.get("unit")
            record.reference_range = item.get("reference_range")
            record.category = item.get("category")
            record.status = item.get("status")
            record.raw_text = item.get("raw_text")
            persisted.append(record)

        db.commit()
        for record in persisted:
            db.refresh(record)
        return persisted

    @staticmethod
    def store_risk_score(
        db: Session,
        user: User,
        *,
        risk_payload: dict[str, Any],
        feature_snapshot: dict[str, Any] | None = None,
        report_id: UUID | str | None = None,
        model_version: str | None = None,
        source: str = "rule_engine",
        status: str = "ready",
        pipeline_run_id: str | None = None,
    ) -> RiskScore:
        score = _as_float(
            risk_payload.get("overall_score")
            or risk_payload.get("risk_score")
            or risk_payload.get("score"),
            default=0.0,
        ) or 0.0

        level_raw = str(risk_payload.get("risk_level") or "").upper()
        try:
            level = RiskLevelEnum(level_raw)
        except Exception:
            level = _risk_level_from_score(score)

        record = None
        if report_id is not None:
            record = (
                db.query(RiskScore)
                .filter(RiskScore.report_id == report_id, RiskScore.user_id == user.id)
                .one_or_none()
            )

        if record is None:
            record = RiskScore(user_id=user.id, report_id=report_id)
            db.add(record)

        record.risk_level = level
        record.overall_score = round(score, 2)
        record.confidence_score = _as_float(risk_payload.get("confidence"), default=None)
        record.ml_model_version = model_version
        record.prediction_source = source
        record.prediction_status = status
        record.feature_snapshot = feature_snapshot
        record.risk_payload = risk_payload
        record.health_score = _as_float(risk_payload.get("health_score"), default=None)
        record.pipeline_run_id = pipeline_run_id or str(uuid4())
        record.is_fallback = source != "ml"

        db.commit()
        db.refresh(record)

        recommendations = risk_payload.get("recommendations") or []
        StoragePipelineService.store_recommendations(db, record, recommendations)
        return record

    @staticmethod
    def store_recommendations(
        db: Session,
        risk_score: RiskScore,
        recommendations: Iterable[Any],
    ) -> list[Recommendation]:
        persisted: list[Recommendation] = []
        for item in recommendations:
            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                category = RecCategoryEnum.LIFESTYLE
                priority = PriorityEnum.MEDIUM
            elif isinstance(item, dict):
                text = str(
                    item.get("detail")
                    or item.get("recommendation_text")
                    or item.get("text")
                    or item.get("title")
                    or ""
                ).strip()
                if not text:
                    continue
                category = _recommendation_category(item.get("category") or item.get("label"))
                priority = _recommendation_priority(item.get("priority"))
            else:
                continue

            record = Recommendation(
                risk_score_id=risk_score.id,
                category=category,
                priority=priority,
                recommendation_text=text,
            )
            db.add(record)
            persisted.append(record)

        if persisted:
            db.commit()
            for record in persisted:
                db.refresh(record)
        return persisted

    @staticmethod
    def store_shap_values(
        db: Session,
        user: User,
        *,
        risk_score: RiskScore,
        shap_entries: Iterable[dict[str, Any]],
        source_type: str = "rule_fallback",
    ) -> list[ShapValueRecord]:
        persisted: list[ShapValueRecord] = []
        for item in shap_entries:
            feature_name = str(item.get("feature_name") or item.get("label") or item.get("key") or "").strip()
            if not feature_name:
                continue

            value = _as_float(item.get("shap_value") or item.get("contribution"), default=0.0) or 0.0
            record = (
                db.query(ShapValueRecord)
                .filter(
                    ShapValueRecord.prediction_id == risk_score.id,
                    ShapValueRecord.feature_name == feature_name,
                )
                .one_or_none()
            )
            if record is None:
                record = ShapValueRecord(
                    prediction_id=risk_score.id,
                    user_id=user.id,
                    feature_name=feature_name,
                    shap_value=value,
                    abs_shap_value=abs(value),
                    direction=str(item.get("direction") or ("increasing" if value >= 0 else "decreasing")),
                    explanation=str(item.get("explanation") or item.get("detail") or ""),
                    source_type=source_type,
                    shap_payload=item,
                )
                db.add(record)
            else:
                record.shap_value = value
                record.abs_shap_value = abs(value)
                record.direction = str(item.get("direction") or ("increasing" if value >= 0 else "decreasing"))
                record.explanation = str(item.get("explanation") or item.get("detail") or "")
                record.source_type = source_type
                record.shap_payload = item
            persisted.append(record)

        if persisted:
            db.commit()
            for record in persisted:
                db.refresh(record)
        return persisted

    @staticmethod
    def store_health_score(
        db: Session,
        user: User,
        *,
        risk_score: RiskScore | None,
        health_payload: dict[str, Any],
        source: str = "pipeline",
    ) -> HealthScoreRecord:
        score = _as_float(health_payload.get("score") or health_payload.get("health_score"), default=0.0) or 0.0
        risk_component = _as_float(health_payload.get("risk_component"), default=None)
        lifestyle_component = _as_float(health_payload.get("lifestyle_component"), default=None)
        vitals_component = _as_float(health_payload.get("vitals_component"), default=None)
        sleep_component = _as_float(health_payload.get("sleep_component"), default=None)

        latest_previous = (
            db.query(HealthScoreRecord)
            .filter(HealthScoreRecord.user_id == user.id)
            .order_by(desc(HealthScoreRecord.calculated_at))
            .first()
        )
        previous_score = _as_float(latest_previous.score if latest_previous else user.health_score, default=None)
        score_change = 0.0
        if previous_score is not None and previous_score != 0:
            score_change = round(score - previous_score, 2)

        record = HealthScoreRecord(
            user_id=user.id,
            risk_score_id=risk_score.id if risk_score else None,
            score=round(score, 2),
            risk_component=risk_component,
            lifestyle_component=lifestyle_component,
            vitals_component=vitals_component,
            sleep_component=sleep_component,
            health_payload=health_payload,
            source=source,
        )
        db.add(record)
        user.health_score = round(score, 2)
        user.score_change_percent = score_change
        if risk_score is not None:
            risk_score.health_score = round(score, 2)

        db.commit()
        db.refresh(record)
        db.refresh(user)
        if risk_score is not None:
            db.refresh(risk_score)
        return record

    @staticmethod
    def latest_feature_snapshot(db: Session, user: User) -> FeatureSnapshotRecord | None:
        return (
            db.query(FeatureSnapshotRecord)
            .filter(FeatureSnapshotRecord.user_id == user.id)
            .order_by(desc(FeatureSnapshotRecord.calculated_at))
            .first()
        )

    @staticmethod
    def latest_risk_score(db: Session, user: User) -> RiskScore | None:
        return (
            db.query(RiskScore)
            .filter(RiskScore.user_id == user.id)
            .order_by(desc(RiskScore.calculated_at))
            .first()
        )

    @staticmethod
    def latest_health_score(db: Session, user: User) -> HealthScoreRecord | None:
        return (
            db.query(HealthScoreRecord)
            .filter(HealthScoreRecord.user_id == user.id)
            .order_by(desc(HealthScoreRecord.calculated_at))
            .first()
        )

    @staticmethod
    def latest_shap_values(db: Session, prediction_id: UUID | str) -> list[ShapValueRecord]:
        return (
            db.query(ShapValueRecord)
            .filter(ShapValueRecord.prediction_id == prediction_id)
            .order_by(desc(ShapValueRecord.calculated_at))
            .all()
        )

    @staticmethod
    def latest_baseline_metrics(db: Session, user: User) -> list[BaselineMetricRecord]:
        return (
            db.query(BaselineMetricRecord)
            .filter(BaselineMetricRecord.user_id == user.id)
            .order_by(desc(BaselineMetricRecord.calculated_at))
            .all()
        )
