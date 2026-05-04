"""Persistence helpers shared by the pipeline stack."""
from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import desc, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import (
    BaselineMetricRecord,
    ClinicalHistory,
    FeatureSnapshotRecord,
    HealthScoreRecord,
    LabResult,
    PriorityEnum,
    Recommendation,
    RecCategoryEnum,
    RiskLevelEnum,
    RiskScore,
    ShapValueRecord,
    User,
)
from pipelines.contracts import PipelineContract
from pipelines.schemas import BaselineMetricDTO
from pipelines.storage_pipeline.utils import ensure_json_safe


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
    def _normalize_health_insights_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        risk = payload.get("risk")
        drivers = payload.get("drivers")
        recommendations = payload.get("recommendations")
        availability = payload.get("availability")

        return {
            "risk": risk if isinstance(risk, dict) else {},
            "drivers": drivers if isinstance(drivers, list) else [],
            "recommendations": recommendations if isinstance(recommendations, list) else [],
            "availability": availability if isinstance(availability, dict) else {
                "has_wearable": False,
                "has_lab": False,
                "has_baseline": False,
            },
        }

    @staticmethod
    def store_feature_snapshot(
        db: Session,
        user: User,
        snapshot: Any,
        *,
        report_id: UUID | str | None = None,
    ) -> FeatureSnapshotRecord:
        feature_payload = ensure_json_safe(getattr(snapshot, "to_dict", lambda: {})())
        if not isinstance(feature_payload, dict):
            feature_payload = {}
        feature_payload.setdefault("hr_mean_7d", float(getattr(snapshot, "hr_mean_7d", 0.0) or 0.0))
        feature_payload.setdefault("steps_avg_7d", float(getattr(snapshot, "steps_avg_7d", 0.0) or 0.0))
        feature_payload.setdefault("sleep_efficiency", float(getattr(snapshot, "sleep_efficiency", 0.0) or 0.0))
        feature_payload.setdefault("data_availability", getattr(snapshot, "data_availability", None) or {"steps": False, "heart_rate": False, "sleep": False})

        record = FeatureSnapshotRecord(
            user_id=user.id,
            report_id=report_id,
            hr_mean_7d=float(getattr(snapshot, "hr_mean_7d", 0.0) or 0.0),
            steps_avg_7d=float(getattr(snapshot, "steps_avg_7d", 0.0) or 0.0),
            sleep_efficiency=float(getattr(snapshot, "sleep_efficiency", 0.0) or 0.0),
            bmi=getattr(snapshot, "bmi", None),
            lifestyle_score=getattr(snapshot, "lifestyle_score", None),
            activity_score=getattr(snapshot, "activity_score", None),
            sleep_score=getattr(snapshot, "sleep_score", None),
            confidence=getattr(snapshot, "confidence", None),
            latest_observation_at=getattr(snapshot, "latest_observation_at", None),
            feature_payload=feature_payload,
            source_breakdown=ensure_json_safe(getattr(snapshot, "source_breakdown", None) or {}),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def store_baseline_metrics(
        db: Session,
        user: User,
        metrics: Iterable[BaselineMetricDTO | dict[str, Any]],
    ) -> list[BaselineMetricRecord]:
        metric_list = list(metrics)
        validated_metrics: list[BaselineMetricDTO] = []
        for metric in metric_list:
            if isinstance(metric, BaselineMetricDTO):
                validated_metrics.append(metric)
                continue

            payload = dict(metric)
            payload.setdefault("user_id", user.id)
            validated_metrics.append(BaselineMetricDTO.model_validate(payload))

        PipelineContract.validate_baseline(validated_metrics)

        persisted: list[BaselineMetricRecord] = []
        for dto in validated_metrics:
            metric = dto.to_storage_dict()
            serialized_metric = dto.to_json_dict()
            serialized_metric["metric_payload"] = ensure_json_safe(serialized_metric.get("metric_payload", {}))
            metric_name = dto.metric_name

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
            record.metric_payload = ensure_json_safe(serialized_metric)
            persisted.append(record)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        for record in persisted:
            db.refresh(record)
        return persisted

    @staticmethod
    def store_lab_results(
        db: Session,
        user: User,
        values: Iterable[dict[str, Any]],
        *,
        report_id: UUID | str | None = None,
    ) -> list[LabResult]:
        persisted: list[LabResult] = []
        for item in values:
            name = str(item.get("name") or item.get("biomarker_name") or "").strip()
            if not name:
                continue

            record = (
                db.query(LabResult)
                .filter(
                    LabResult.user_id == user.id,
                    LabResult.report_id == report_id,
                    LabResult.name == name,
                )
                .one_or_none()
            )
            if record is None:
                record = LabResult(user_id=user.id, report_id=report_id, name=name)
                db.add(record)

            loinc_code = str(item.get("loinc_code") or item.get("loinc") or "").strip()
            if loinc_code:
                record.loinc_code = loinc_code
            record.value = float(item.get("value") or item.get("raw_value") or 0.0)
            record.unit = item.get("unit")
            record.reference_range = item.get("reference_range")
            record.category = item.get("category")
            record.status = item.get("status")
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
    ) -> list[LabResult]:
        return StoragePipelineService.store_lab_results(db, user, values, report_id=report_id)

    @staticmethod
    def store_risk_score(
        db: Session,
        user: User,
        *,
        risk_payload: dict[str, Any],
        feature_snapshot_id: UUID | str | None = None,
        report_id: UUID | str | None = None,
        model_version: str | None = None,
        source: str = "rule_engine",
        status: str = "ready",
        run_id: str | None = None,
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

        sanitized_payload = dict(risk_payload or {})
        sanitized_payload.pop("feature_snapshot", None)

        effective_run_id = run_id or str(uuid4())
        record = (
            db.query(RiskScore)
            .filter(RiskScore.user_id == user.id, RiskScore.run_id == effective_run_id)
            .one_or_none()
        )
        if record is None:
            record = RiskScore(user_id=user.id)
            db.add(record)
        else:
            db.query(Recommendation).filter(Recommendation.risk_score_id == record.id).delete(synchronize_session=False)

        if report_id is not None:
            record.report_id = report_id
        if feature_snapshot_id is not None:
            record.feature_snapshot_id = feature_snapshot_id
        elif isinstance(risk_payload.get("feature_snapshot_id"), str):
            feature_snapshot_record = (
                db.query(FeatureSnapshotRecord)
                .filter(
                    FeatureSnapshotRecord.id == risk_payload.get("feature_snapshot_id"),
                    FeatureSnapshotRecord.user_id == user.id,
                )
                .one_or_none()
            )
            if feature_snapshot_record is not None:
                record.feature_snapshot_id = feature_snapshot_record.id

        record.risk_level = level
        record.overall_score = round(score, 2)
        record.confidence_score = _as_float(risk_payload.get("confidence"), default=None)
        record.model_version = model_version
        record.prediction_source = source
        record.prediction_status = status
        record.risk_payload = ensure_json_safe(sanitized_payload)
        record.health_score = _as_float(sanitized_payload.get("health_score"), default=None)
        record.run_id = effective_run_id
        record.is_fallback = source != "ml"

        db.commit()
        db.refresh(record)

        recommendations = (record.risk_payload or {}).get("recommendations") or []
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
        normalized_entries: dict[str, dict[str, Any]] = {}
        ordered_feature_names: list[str] = []
        for item in shap_entries:
            feature_name = str(item.get("feature_name") or item.get("label") or item.get("key") or "").strip()
            if not feature_name:
                continue

            raw_value = item.get("shap_value") if item.get("shap_value") is not None else item.get("contribution")
            value = _as_float(raw_value, default=0.0) or 0.0
            if feature_name not in normalized_entries:
                ordered_feature_names.append(feature_name)

            normalized_entries[feature_name] = {
                "prediction_id": risk_score.id,
                "user_id": user.id,
                "feature_name": feature_name,
                "shap_value": value,
                "abs_shap_value": abs(value),
                "direction": str(item.get("direction") or ("increasing" if value >= 0 else "decreasing")),
                "explanation": str(item.get("explanation") or item.get("detail") or ""),
                "source_type": source_type,
                "shap_payload": ensure_json_safe(item),
            }

        if not normalized_entries:
            return []

        try:
            for feature_name in ordered_feature_names:
                values = normalized_entries[feature_name]
                stmt = insert(ShapValueRecord).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["prediction_id", "feature_name"],
                    set_={
                        "shap_value": stmt.excluded.shap_value,
                        "abs_shap_value": stmt.excluded.abs_shap_value,
                        "direction": stmt.excluded.direction,
                        "explanation": stmt.excluded.explanation,
                        "source_type": stmt.excluded.source_type,
                        "shap_payload": stmt.excluded.shap_payload,
                        "updated_at": func.now(),
                    },
                )
                db.execute(stmt)
            db.commit()
        except Exception:
            db.rollback()
            raise

        persisted = (
            db.query(ShapValueRecord)
            .filter(
                ShapValueRecord.prediction_id == risk_score.id,
                ShapValueRecord.feature_name.in_(ordered_feature_names),
            )
            .all()
        )
        persisted_by_feature = {record.feature_name: record for record in persisted}
        return [
            persisted_by_feature[feature_name]
            for feature_name in ordered_feature_names
            if feature_name in persisted_by_feature
        ]

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
            health_payload=ensure_json_safe(health_payload),
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
    def store_health_insights(
        db: Session,
        user: User,
        insights_payload: dict[str, Any] | None,
        *,
        prediction_id: UUID | str | None = None,
    ) -> RiskScore | None:
        normalized = StoragePipelineService._normalize_health_insights_payload(insights_payload)
        record = None
        if prediction_id is not None:
            record = (
                db.query(RiskScore)
                .filter(RiskScore.id == prediction_id, RiskScore.user_id == user.id)
                .one_or_none()
            )

        if record is None:
            record = StoragePipelineService.latest_risk_score(db, user)

        if record is None:
            return None

        risk_payload = dict(record.risk_payload or {})
        risk_payload["health_insights"] = ensure_json_safe(normalized)
        risk_payload["drivers"] = normalized["drivers"] or list(risk_payload.get("drivers") or [])
        risk_payload["recommendations"] = normalized["recommendations"] or list(risk_payload.get("recommendations") or [])
        if normalized["risk"]:
            existing_risks = risk_payload.get("risks")
            risk_payload["risks"] = normalized["risk"] if not isinstance(existing_risks, dict) or not existing_risks else existing_risks

        record.risk_payload = ensure_json_safe(risk_payload)
        db.commit()
        db.refresh(record)
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
            .order_by(desc(RiskScore.calculated_at), desc(RiskScore.created_at))
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

    @staticmethod
    def latest_clinical_history(db: Session, user: User) -> ClinicalHistory | None:
        return (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user.id)
            .order_by(desc(ClinicalHistory.created_at))
            .first()
        )

    @staticmethod
    def fetch_health_insights(db: Session, user: User) -> dict[str, Any] | None:
        latest_risk = StoragePipelineService.latest_risk_score(db, user)
        if latest_risk is None:
            return None

        risk_payload = latest_risk.risk_payload if isinstance(latest_risk.risk_payload, dict) else {}
        stored = StoragePipelineService._normalize_health_insights_payload(risk_payload.get("health_insights"))
        cached_explanation = risk_payload.get("rag_explanation") if isinstance(risk_payload.get("rag_explanation"), dict) else {}
        explanation_payload = cached_explanation.get("payload") if isinstance(cached_explanation.get("payload"), dict) else None

        base_risk = stored["risk"]
        if not base_risk:
            fallback_risks = risk_payload.get("risks")
            if isinstance(fallback_risks, dict):
                base_risks = dict(fallback_risks)
            else:
                base_risks = {}
            base_risks.setdefault("overall_risk_score", float(latest_risk.overall_score) if latest_risk.overall_score is not None else 0.0)
            if getattr(latest_risk, "risk_level", None) is not None:
                base_risks.setdefault(
                    "risk_level",
                    latest_risk.risk_level.value if hasattr(latest_risk.risk_level, "value") else str(latest_risk.risk_level),
                )
            base_risk = base_risks

        drivers = stored["drivers"]
        if not drivers:
            payload_drivers = risk_payload.get("drivers")
            drivers = payload_drivers if isinstance(payload_drivers, list) else []
        if not drivers:
            shap_rows = StoragePipelineService.latest_shap_values(db, latest_risk.id)
            drivers = [
                {
                    "feature_name": row.feature_name,
                    "shap_value": float(row.shap_value),
                    "abs_shap_value": float(row.abs_shap_value),
                    "direction": row.direction,
                    "explanation": row.explanation,
                    "source_type": row.source_type,
                    "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
                }
                for row in shap_rows
            ]

        recommendations = stored["recommendations"]
        if not recommendations:
            payload_recommendations = risk_payload.get("recommendations")
            recommendations = payload_recommendations if isinstance(payload_recommendations, list) else []

        has_lab = (
            db.query(LabResult.id)
            .filter(LabResult.user_id == user.id)
            .order_by(desc(LabResult.timestamp))
            .first()
            is not None
        )
        latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
        linked_feature = getattr(latest_risk, "feature_snapshot_record", None)
        feature_payload = {}
        if linked_feature and isinstance(linked_feature.feature_payload, dict):
            feature_payload = linked_feature.feature_payload
        elif isinstance(getattr(latest_risk, "feature_snapshot", None), dict):
            feature_payload = latest_risk.feature_snapshot
        elif latest_feature and isinstance(latest_feature.feature_payload, dict):
            feature_payload = latest_feature.feature_payload
        source_breakdown = feature_payload.get("source_breakdown") if isinstance(feature_payload, dict) else {}
        if not isinstance(source_breakdown, dict):
            source_breakdown = {}

        availability = stored["availability"]
        availability = {
            **availability,
            "has_wearable": bool(
                sum(
                    int(source_breakdown.get(key) or 0)
                    for key in ("heart_rate_points", "step_points", "sleep_points", "wearable_sleep_rows", "bp_points")
                )
            ),
            "has_lab": bool(has_lab),
            "has_baseline": bool(StoragePipelineService.latest_baseline_metrics(db, user)),
        }

        clinical_history_payload = None
        latest_clinical_history = StoragePipelineService.latest_clinical_history(db, user)
        if latest_clinical_history is not None:
            try:
                from services.clinical_history_service import ClinicalHistoryService

                clinical_history_payload = ClinicalHistoryService.serialize(
                    latest_clinical_history,
                    feature_payload=feature_payload,
                )
            except Exception:
                clinical_history_payload = None

        return {
            "risk": base_risk if isinstance(base_risk, dict) else {},
            "drivers": drivers if isinstance(drivers, list) else [],
            "recommendations": recommendations if isinstance(recommendations, list) else [],
            "availability": availability,
            "analysis": risk_payload.get("analysis"),
            "explanation": explanation_payload,
            "confidence": float(latest_risk.confidence_score) if latest_risk.confidence_score is not None else None,
            "feature_snapshot": latest_risk.feature_snapshot if isinstance(latest_risk.feature_snapshot, dict) else feature_payload,
            "clinical_history": clinical_history_payload,
            "clinical_features": (
                clinical_history_payload.get("analysis", {}).get("ml_features", {})
                if isinstance(clinical_history_payload, dict)
                else {}
            ),
            "data_points": risk_payload.get("data_points"),
            "last_updated": latest_risk.calculated_at.isoformat() if latest_risk.calculated_at else None,
        }
