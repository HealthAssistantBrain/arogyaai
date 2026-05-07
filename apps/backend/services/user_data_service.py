"""
User data service — canonical profile, settings, onboarding, and vitals storage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.utils import safe_input
from models import (
    User,
    UserProfile,
    UserSetting,
    UserVital,
    UserVitalSourceEnum,
    UserVitalTypeEnum,
    WearableMetric,
)
from pipelines.ingestion_pipeline.service import IngestionPipelineService
from services.onboarding_service import OnboardingService
from services.user_service import UserService

ALLOWED_FETCH_INTERVALS = {5, 10, 15, 20, 25, 30}
RANGE_WINDOWS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _current_local_day_bounds(timezone_name: str | None = None) -> tuple[datetime, datetime]:
    candidate = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE or "Asia/Kolkata"
    try:
        tzinfo = ZoneInfo(candidate)
    except Exception:
        tzinfo = ZoneInfo("Asia/Kolkata")
    now_local = datetime.now(tzinfo)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc), now_local.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        # Accept either epoch seconds or epoch milliseconds.
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000.0
        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp format") from exc

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp value")


def _classify_blood_pressure_values(systolic: float | None, diastolic: float | None) -> str:
    if systolic is None and diastolic is None:
        return "missing"
    if systolic is None or diastolic is None:
        return "partial"
    if float(systolic) == float(diastolic):
        return "duplicate"
    return "pair"


def _coerce_blood_pressure_value(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_blood_pressure_pair_from_metadata(metadata: dict[str, Any] | None) -> tuple[float | None, float | None]:
    metadata = metadata if isinstance(metadata, dict) else {}
    return (
        _coerce_blood_pressure_value(metadata.get("systolic")),
        _coerce_blood_pressure_value(metadata.get("diastolic")),
    )


def _serialize_setting(setting: UserSetting, user_id: str) -> dict:
    return {
        "id": str(setting.id),
        "user_id": user_id,
        "auto_fetch_enabled": bool(setting.auto_fetch_enabled),
        "fetch_interval_minutes": int(setting.fetch_interval_minutes),
        "last_fetch_at": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
    }


def _serialize_vital(vital: UserVital) -> dict:
    return {
        "id": str(vital.id),
        "user_id": str(vital.user_id),
        "type": vital.vital_type.value,
        "value": float(vital.value),
        "unit": vital.unit,
        "raw_value": float(vital.raw_value) if vital.raw_value is not None else None,
        "raw_unit": vital.raw_unit,
        "normalized_value": float(vital.normalized_value) if vital.normalized_value is not None else float(vital.value),
        "normalized_unit": vital.normalized_unit or vital.unit,
        "timestamp": vital.timestamp.isoformat() if vital.timestamp else None,
        "source": vital.source.value,
        "created_at": vital.created_at.isoformat() if vital.created_at else None,
    }


class UserDataService:
    @staticmethod
    def get_or_create_profile(db: Session, user: User) -> UserProfile:
        return UserService.get_or_create_user_profile(db, user)

    @staticmethod
    def get_or_create_settings(db: Session, user: User) -> UserSetting:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
        if setting:
            return setting

        setting = UserSetting(
            user_id=user.id,
            auto_fetch_enabled=False,
            fetch_interval_minutes=15,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def get_profile(db: Session, user: User) -> dict:
        return UserService.get_user_profile(db, user)

    @staticmethod
    def update_profile(db: Session, user: User, updates: dict) -> dict:
        normalized = dict(updates or {})
        if "date_of_birth" not in normalized and "dob" in normalized:
            normalized["date_of_birth"] = normalized["dob"]
        if "phone_number" not in normalized and "phone" in normalized:
            normalized["phone_number"] = normalized["phone"]
        if "height_cm" not in normalized and "height" in normalized:
            normalized["height_cm"] = normalized["height"]
        if "weight_kg" not in normalized and "weight" in normalized:
            normalized["weight_kg"] = normalized["weight"]

        payload = {}
        if "full_name" in normalized:
            payload["full_name"] = safe_input(normalized.get("full_name"))
        if "avatar_url" in normalized:
            payload["avatar_url"] = normalized.get("avatar_url")
        if "phone_number" in normalized:
            payload["phone_number"] = normalized.get("phone_number")
        if "date_of_birth" in normalized:
            payload["date_of_birth"] = normalized.get("date_of_birth")
        if "age" in normalized:
            payload["age"] = normalized.get("age")
        if "gender" in normalized:
            payload["gender"] = normalized.get("gender")
        if "occupation" in normalized:
            payload["occupation"] = normalized.get("occupation")
        if "city" in normalized:
            payload["city"] = normalized.get("city")
        if "marital_status" in normalized:
            payload["marital_status"] = normalized.get("marital_status")
        if "height_cm" in normalized:
            payload["height_cm"] = normalized.get("height_cm")
        if "weight_kg" in normalized:
            payload["weight_kg"] = normalized.get("weight_kg")
        if "activity_level" in normalized:
            payload["activity_level"] = normalized.get("activity_level")
        if "goals" in normalized:
            payload["goals"] = normalized.get("goals")
        if "family_history" in normalized:
            payload["family_history"] = normalized.get("family_history")
        if "surgeries" in normalized:
            payload["surgeries"] = normalized.get("surgeries")
        if "hospitalizations" in normalized:
            payload["hospitalizations"] = normalized.get("hospitalizations")
        if "hospitalization_details" in normalized:
            payload["hospitalization_details"] = normalized.get("hospitalization_details")
        if "current_medications" in normalized or "medications" in normalized:
            payload["current_medications"] = normalized.get("current_medications", normalized.get("medications"))
        if "sleep_hours" in normalized or "sleep" in normalized:
            payload["sleep_hours"] = normalized.get("sleep_hours", normalized.get("sleep"))
        if "stress_level" in normalized or "stress" in normalized:
            payload["stress_level"] = normalized.get("stress_level", normalized.get("stress"))
        if "smoking" in normalized:
            payload["smoking"] = normalized.get("smoking")
        if "alcohol" in normalized:
            payload["alcohol"] = normalized.get("alcohol")
        if "appetite" in normalized:
            payload["appetite"] = normalized.get("appetite")
        if "bowel_habits" in normalized:
            payload["bowel_habits"] = normalized.get("bowel_habits")
        if "blood_group" in normalized:
            payload["blood_group"] = normalized.get("blood_group")
        if "allergies" in normalized:
            payload["allergies"] = normalized.get("allergies")
        return UserService.update_user_profile(db, user, payload)

    @staticmethod
    def save_onboarding(db: Session, user: User, payload: dict) -> dict:
        normalized = dict(payload or {})
        if "date_of_birth" not in normalized and "dob" in normalized:
            normalized["date_of_birth"] = normalized["dob"]
        if "phone_number" not in normalized and "phone" in normalized:
            normalized["phone_number"] = normalized["phone"]
        if "height_cm" not in normalized and "height" in normalized:
            normalized["height_cm"] = normalized["height"]
        if "weight_kg" not in normalized and "weight" in normalized:
            normalized["weight_kg"] = normalized["weight"]
        if "activity_level" in normalized:
            normalized["activity_level"] = normalized.get("activity_level")

        profile_payload = {
            key: normalized.get(key)
            for key in (
                "full_name",
                "date_of_birth",
                "age",
                "gender",
                "occupation",
                "city",
                "marital_status",
                "phone_number",
                "height_cm",
                "weight_kg",
                "activity_level",
                "goals",
                "family_history",
                "surgeries",
                "hospitalizations",
                "hospitalization_details",
                "current_medications",
                "sleep_hours",
                "stress_level",
                "smoking",
                "alcohol",
                "appetite",
                "bowel_habits",
                "blood_group",
                "allergies",
            )
            if key in normalized and normalized.get(key) is not None
        }
        result = UserDataService.update_profile(db, user, profile_payload)

        user_updates = {}
        if normalized.get("is_onboarding_done") is not None:
            user_updates["is_onboarding_done"] = bool(normalized.get("is_onboarding_done"))
        if normalized.get("onboarding_step") is not None:
            user_updates["onboarding_step"] = int(normalized.get("onboarding_step"))

        if user_updates:
            UserService.update_user_me(db, user, user_updates)

        if user_updates.get("is_onboarding_done"):
            return OnboardingService.finalize_onboarding(db, user, normalized)

        return result

    @staticmethod
    def get_settings(db: Session, user: User) -> dict:
        setting = UserDataService.get_or_create_settings(db, user)
        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": _serialize_setting(setting, str(user.id)),
            "last_updated": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
        }

    @staticmethod
    def update_settings(db: Session, user: User, payload: dict) -> dict:
        setting = UserDataService.get_or_create_settings(db, user)

        auto_fetch_enabled = payload.get("auto_fetch_enabled")
        fetch_interval_minutes = payload.get("fetch_interval_minutes")

        if auto_fetch_enabled is None or fetch_interval_minutes is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="auto_fetch_enabled and fetch_interval_minutes are required",
            )

        interval = int(fetch_interval_minutes)
        if interval not in ALLOWED_FETCH_INTERVALS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fetch_interval_minutes must be one of [5, 10, 15, 20, 25, 30]",
            )

        setting.auto_fetch_enabled = bool(auto_fetch_enabled)
        setting.fetch_interval_minutes = interval
        db.commit()
        db.refresh(setting)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": _serialize_setting(setting, str(user.id)),
            "last_updated": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
        }

    @staticmethod
    def list_vitals(
        db: Session,
        user: User,
        vital_type: Optional[str] = None,
        range_value: str = "24h",
    ) -> dict:
        query = db.query(UserVital).filter(UserVital.user_id == user.id)
        enum_value: UserVitalTypeEnum | None = None

        if vital_type:
            try:
                enum_value = UserVitalTypeEnum(vital_type.strip().lower())
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vital type") from exc
            query = query.filter(UserVital.vital_type == enum_value)

        if range_value and range_value != "all":
            window = RANGE_WINDOWS.get(range_value)
            if window is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid range value")
            query = query.filter(UserVital.timestamp >= _now_utc() - window)

        vitals = query.order_by(UserVital.timestamp.asc()).all()
        payload = [_serialize_vital(vital) for vital in vitals]

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "vitals": payload,
                "total_count": len(payload),
                "type": vital_type,
                "range": range_value,
            },
            "last_updated": payload[-1]["timestamp"] if payload else None,
        }

    @staticmethod
    def store_vitals(
        db: Session,
        user: User,
        records: Iterable[dict],
        *,
        overwrite_window: bool = False,
        overwrite_types: Iterable[UserVitalTypeEnum | str] | None = None,
        window_start: Any = None,
        window_end: Any = None,
    ) -> list[UserVital]:
        saved: list[UserVital] = []
        normalized_records: dict[tuple[UserVitalTypeEnum, datetime, UserVitalSourceEnum], dict[str, Any]] = {}
        record_payloads = list(records or [])
        validated_payloads = IngestionPipelineService.normalize_vital_records(record_payloads)
        if validated_payloads:
            record_payloads = validated_payloads

        for record in record_payloads:
            vital_type = record.get("type")
            if not vital_type:
                continue

            try:
                vital_enum = UserVitalTypeEnum(str(vital_type).strip().lower())
            except ValueError:
                continue

            try:
                source_enum = UserVitalSourceEnum(str(record.get("source") or "google_fit").strip().lower())
            except ValueError:
                source_enum = UserVitalSourceEnum.GOOGLE_FIT

            timestamp = _parse_timestamp(record.get("timestamp"))
            value_raw = record.get("normalized_value", record.get("value"))
            if value_raw is None:
                continue
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                continue
            if value < 0 or (
                value == 0
                and vital_enum not in {UserVitalTypeEnum.STEPS, UserVitalTypeEnum.CALORIES_BURNED}
            ):
                continue
            unit = str(record.get("normalized_unit") or record.get("unit") or "")
            if not unit:
                continue

            raw_value_raw = record.get("raw_value")
            if raw_value_raw is None:
                raw_value = value
            else:
                try:
                    raw_value = float(raw_value_raw)
                except (TypeError, ValueError):
                    raw_value = value

            raw_unit = str(record.get("raw_unit") or unit)
            normalized_value = value
            normalized_unit = unit

            normalized_records[(vital_enum, timestamp, source_enum)] = {
                "vital_type": vital_enum,
                "source": source_enum,
                "timestamp": timestamp,
                "value": value,
                "unit": unit,
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "normalized_value": normalized_value,
                "normalized_unit": normalized_unit,
            }

        bp_values_by_timestamp: dict[tuple[datetime, UserVitalSourceEnum], dict[str, float]] = {}
        for item in normalized_records.values():
            bp_key = (item["timestamp"], item["source"])
            if item["vital_type"] == UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC:
                bp_values_by_timestamp.setdefault(bp_key, {})["systolic"] = item["value"]
            elif item["vital_type"] == UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC:
                bp_values_by_timestamp.setdefault(bp_key, {})["diastolic"] = item["value"]

        for (timestamp, source), bp_values in bp_values_by_timestamp.items():
            systolic = bp_values.get("systolic")
            diastolic = bp_values.get("diastolic")
            bp_state = _classify_blood_pressure_values(systolic, diastolic)
            logger.info(
                "BP_VALIDATION | stage=db_validation | user_id=%s | timestamp=%s | source=%s | status=%s | systolic=%s | diastolic=%s",
                str(user.id),
                timestamp.isoformat(),
                source.value,
                bp_state,
                systolic,
                diastolic,
            )
            if bp_state == "duplicate":
                logger.warning(
                    "INVALID_BP_BLOCKED | stage=db_validation | user_id=%s | timestamp=%s | source=%s | function_name=store_vitals | systolic=%s | diastolic=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    source.value,
                    systolic,
                    diastolic,
                )
                logger.warning(
                    "BP_SKIPPED_INVALID | stage=db_validation | user_id=%s | timestamp=%s | source=%s | systolic=%s | diastolic=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    source.value,
                    systolic,
                    diastolic,
                )
                continue

            if bp_state == "pair":
                logger.info(
                    "BP_PARSED | stage=db_validation | user_id=%s | timestamp=%s | source=%s | systolic=%s | diastolic=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    source.value,
                    systolic,
                    diastolic,
                )
            logger.info(
                "BP_DB_WRITE | stage=db_validation | user_id=%s | timestamp=%s | source=%s | status=%s | systolic=%s | diastolic=%s",
                str(user.id),
                timestamp.isoformat(),
                source.value,
                bp_state,
                systolic,
                diastolic,
            )

        invalid_bp_keys = {
            bp_key
            for bp_key, bp_values in bp_values_by_timestamp.items()
            if _classify_blood_pressure_values(bp_values.get("systolic"), bp_values.get("diastolic")) == "duplicate"
        }
        if invalid_bp_keys:
            normalized_records = {
                key: item
                for key, item in normalized_records.items()
                if not (
                    item["vital_type"] in {
                        UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC,
                        UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC,
                    }
                    and (item["timestamp"], item["source"]) in invalid_bp_keys
                )
            }

        delete_types: set[UserVitalTypeEnum] = set()
        if overwrite_types is not None:
            for item in overwrite_types:
                try:
                    delete_types.add(item if isinstance(item, UserVitalTypeEnum) else UserVitalTypeEnum(str(item).strip().lower()))
                except ValueError:
                    continue
        elif overwrite_window:
            delete_types = {item["vital_type"] for item in normalized_records.values()}

        if overwrite_window and delete_types:
            start_at = _parse_timestamp(window_start) if window_start is not None else None
            end_at = _parse_timestamp(window_end) if window_end is not None else None
            if start_at is None and normalized_records:
                start_at = min(item["timestamp"] for item in normalized_records.values())
            if end_at is None and normalized_records:
                end_at = max(item["timestamp"] for item in normalized_records.values())

            if start_at is not None and end_at is not None and start_at < end_at:
                (
                    db.query(UserVital)
                    .filter(
                        UserVital.user_id == user.id,
                        UserVital.vital_type.in_(list(delete_types)),
                        UserVital.source == UserVitalSourceEnum.GOOGLE_FIT,
                        UserVital.timestamp >= start_at,
                        UserVital.timestamp < end_at,
                    )
                    .delete(synchronize_session=False)
                )

        for item in normalized_records.values():
            vital_enum = item["vital_type"]
            source_enum = item["source"]
            timestamp = item["timestamp"]
            value = item["value"]
            unit = item["unit"]
            raw_value = item["raw_value"]
            raw_unit = item["raw_unit"]
            normalized_value = item["normalized_value"]
            normalized_unit = item["normalized_unit"]

            existing = (
                db.query(UserVital)
                .filter(
                    UserVital.user_id == user.id,
                    UserVital.vital_type == vital_enum,
                    UserVital.timestamp == timestamp,
                    UserVital.source == source_enum,
                )
                .first()
            )

            if existing:
                existing.value = value
                existing.unit = unit
                existing.raw_value = raw_value
                existing.raw_unit = raw_unit
                existing.normalized_value = normalized_value
                existing.normalized_unit = normalized_unit
                vital = existing
            else:
                vital = UserVital(
                    user_id=user.id,
                    vital_type=vital_enum,
                    value=value,
                    unit=unit,
                    raw_value=raw_value,
                    raw_unit=raw_unit,
                    normalized_value=normalized_value,
                    normalized_unit=normalized_unit,
                    timestamp=timestamp,
                    source=source_enum,
                )
                db.add(vital)
            logger.info(
                "METRIC_DB_WRITE | storage=user_vitals | user_id=%s | metric_type=%s | timestamp=%s | source=%s | value=%s | unit=%s | raw_value=%s | raw_unit=%s | normalized_value=%s | normalized_unit=%s",
                str(user.id),
                vital_enum.value,
                timestamp.isoformat(),
                source_enum.value,
                value,
                unit,
                raw_value,
                raw_unit,
                normalized_value,
                normalized_unit,
            )
            if vital_enum == UserVitalTypeEnum.GLUCOSE:
                logger.info(
                    "GLUCOSE_PIPELINE_TRACE | stage=db_write | user_id=%s | timestamp=%s | raw_value=%s | raw_unit=%s | normalized_value=%s | normalized_unit=%s | stored_value=%s | stored_unit=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    raw_value,
                    raw_unit,
                    normalized_value,
                    normalized_unit,
                    value,
                    unit,
                )
            if vital_enum in {
                UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC,
                UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC,
            }:
                logger.info(
                    "BP_DB_WRITE | stage=db_upsert | user_id=%s | type=%s | timestamp=%s | source=%s | value=%s",
                    str(user.id),
                    vital_enum.value,
                    timestamp.isoformat(),
                    source_enum.value,
                    value,
                )
            saved.append(vital)

        if saved or (overwrite_window and delete_types):
            db.commit()
            for item in saved:
                db.refresh(item)

        return saved

    @staticmethod
    def store_wearable_metrics(db: Session, user: User, records: Iterable[dict]) -> list[WearableMetric]:
        saved: list[WearableMetric] = []
        normalized_records: dict[tuple[str, datetime, str], dict[str, Any]] = {}

        for record in records or []:
            metric_type = str(record.get("metric_type") or record.get("type") or "").strip().lower()
            if not metric_type:
                continue

            value_raw = record.get("value")
            if value_raw is None:
                continue
            try:
                numeric_value = float(value_raw)
            except (TypeError, ValueError):
                continue
            if numeric_value < 0 and metric_type != "location":
                continue

            unit = str(record.get("unit") or "").strip()
            if not unit:
                continue

            timestamp = _parse_timestamp(record.get("timestamp"))
            source = str(record.get("source") or "google_fit").strip().lower() or "google_fit"
            metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
            extra_metadata = {
                key: value
                for key, value in record.items()
                if key not in {"type", "metric_type", "value", "unit", "timestamp", "source", "timezone", "metadata"}
            }
            if record.get("timezone"):
                metadata = {**metadata, "timezone": record.get("timezone")}
            metadata = {**metadata, **extra_metadata}

            if metric_type == "blood_pressure":
                systolic, diastolic = _extract_blood_pressure_pair_from_metadata(metadata)
                bp_state = _classify_blood_pressure_values(systolic, diastolic)
                logger.info(
                    "BP_VALIDATION | stage=wearable_metric_validation | user_id=%s | timestamp=%s | source=%s | status=%s | systolic=%s | diastolic=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    source,
                    bp_state,
                    systolic,
                    diastolic,
                )
                if bp_state == "duplicate":
                    logger.warning(
                        "INVALID_BP_BLOCKED | stage=wearable_metric_validation | user_id=%s | timestamp=%s | source=%s | function_name=store_wearable_metrics | systolic=%s | diastolic=%s",
                        str(user.id),
                        timestamp.isoformat(),
                        source,
                        systolic,
                        diastolic,
                    )
                    continue
                logger.info(
                    "BP_DB_WRITE | stage=wearable_metric_validation | user_id=%s | timestamp=%s | source=%s | status=%s | systolic=%s | diastolic=%s",
                    str(user.id),
                    timestamp.isoformat(),
                    source,
                    bp_state,
                    systolic,
                    diastolic,
                )

            normalized_records[(metric_type, timestamp, source)] = {
                "metric_type": metric_type,
                "value": numeric_value,
                "unit": unit,
                "timestamp": timestamp,
                "source": source,
                "metadata": metadata,
            }

        for item in normalized_records.values():
            existing = (
                db.query(WearableMetric)
                .filter(
                    WearableMetric.user_id == user.id,
                    WearableMetric.metric_type == item["metric_type"],
                    WearableMetric.timestamp == item["timestamp"],
                    WearableMetric.source == item["source"],
                )
                .first()
            )

            if existing:
                existing.value = item["value"]
                existing.unit = item["unit"]
                existing.metric_metadata = item["metadata"]
                wearable_metric = existing
            else:
                wearable_metric = WearableMetric(
                    user_id=user.id,
                    metric_type=item["metric_type"],
                    value=item["value"],
                    unit=item["unit"],
                    timestamp=item["timestamp"],
                    source=item["source"],
                    metric_metadata=item["metadata"],
                )
                db.add(wearable_metric)
            logger.info(
                "METRIC_DB_WRITE | storage=wearable_metrics | user_id=%s | metric_type=%s | timestamp=%s | source=%s | value=%s | unit=%s | metadata_keys=%s",
                str(user.id),
                item["metric_type"],
                item["timestamp"].isoformat(),
                item["source"],
                item["value"],
                item["unit"],
                sorted(item["metadata"].keys()),
            )
            saved.append(wearable_metric)

        if saved:
            db.commit()
            for item in saved:
                db.refresh(item)

        return saved

    @staticmethod
    def touch_settings_fetch(db: Session, user: User) -> None:
        setting = UserDataService.get_or_create_settings(db, user)
        setting.last_fetch_at = _now_utc()
        db.commit()
