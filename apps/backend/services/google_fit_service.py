import asyncio
import uuid
import logging
import os
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import certifi
import httpx
import jwt
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from core.config import settings
from core.security import decrypt_secret, encrypt_secret
from models import (
    Device,
    DeviceTypeEnum,
    GoogleFitConnection,
    PROVIDER_GOOGLE_FIT,
    User,
    UserDevice,
    UserVital,
    UserVitalSourceEnum,
    UserVitalTypeEnum,
)
from pipelines.ingestion_pipeline.service import compute_daily_step_summary, compute_daily_steps
from pipelines.orchestrator import run_pipeline
from services.alert_service import generate_health_alerts
from services.user_data_service import UserDataService
from services.event_service import emit_event

GOOGLE_FIT_ACTIVITY_SCOPE = "https://www.googleapis.com/auth/fitness.activity.read"
GOOGLE_FIT_BODY_SCOPE = "https://www.googleapis.com/auth/fitness.body.read"
GOOGLE_FIT_HEART_RATE_SCOPE = "https://www.googleapis.com/auth/fitness.heart_rate.read"
GOOGLE_FIT_LOCATION_SCOPE = "https://www.googleapis.com/auth/fitness.location.read"
GOOGLE_FIT_SLEEP_SCOPE = "https://www.googleapis.com/auth/fitness.sleep.read"
GOOGLE_FIT_BLOOD_GLUCOSE_SCOPE = "https://www.googleapis.com/auth/fitness.blood_glucose.read"
GOOGLE_FIT_BLOOD_PRESSURE_SCOPE = "https://www.googleapis.com/auth/fitness.blood_pressure.read"
GOOGLE_FIT_BODY_TEMPERATURE_SCOPE = "https://www.googleapis.com/auth/fitness.body_temperature.read"
GOOGLE_FIT_OXYGEN_SCOPE = "https://www.googleapis.com/auth/fitness.oxygen_saturation.read"
GOOGLE_FIT_SCOPE_SET = [
    "openid",
    "email",
    "profile",
    GOOGLE_FIT_ACTIVITY_SCOPE,
    GOOGLE_FIT_BODY_SCOPE,
    GOOGLE_FIT_HEART_RATE_SCOPE,
    GOOGLE_FIT_LOCATION_SCOPE,
    GOOGLE_FIT_SLEEP_SCOPE,
    GOOGLE_FIT_BLOOD_GLUCOSE_SCOPE,
    GOOGLE_FIT_BLOOD_PRESSURE_SCOPE,
    GOOGLE_FIT_BODY_TEMPERATURE_SCOPE,
    GOOGLE_FIT_OXYGEN_SCOPE,
]
GOOGLE_FIT_STEP_DATA_TYPE = "com.google.step_count.delta"
GOOGLE_FIT_HEART_RATE_DATA_TYPE = "com.google.heart_rate.bpm"
GOOGLE_FIT_SLEEP_DATA_TYPE = "com.google.sleep.segment"
GOOGLE_FIT_SPO2_DATA_TYPE = "com.google.oxygen_saturation"
GOOGLE_FIT_SPO2_SUMMARY_DATA_TYPE = "com.google.oxygen_saturation.summary"
GOOGLE_FIT_GLUCOSE_DATA_TYPE = "com.google.blood_glucose"
GOOGLE_FIT_GLUCOSE_SUMMARY_DATA_TYPE = "com.google.blood_glucose.summary"
GOOGLE_FIT_BLOOD_PRESSURE_DATA_TYPE = "com.google.blood_pressure"
GOOGLE_FIT_BLOOD_PRESSURE_SUMMARY_DATA_TYPE = "com.google.blood_pressure.summary"
GOOGLE_FIT_BODY_TEMPERATURE_DATA_TYPE = "com.google.body.temperature"
GOOGLE_FIT_BODY_TEMPERATURE_SUMMARY_DATA_TYPE = "com.google.body.temperature.summary"
GOOGLE_FIT_LOCATION_DATA_TYPE = "com.google.location.sample"
GOOGLE_FIT_DATASOURCE_ID = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
GOOGLE_FIT_MERGED_HEART_RATE_DATASOURCE_ID = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_FIT_AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
GOOGLE_FIT_DATA_SOURCE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataSources"
GOOGLE_FIT_SESSIONS_URL = "https://www.googleapis.com/fitness/v1/users/me/sessions"
GOOGLE_FIT_SLEEP_ACTIVITY_TYPE = 72
GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS = 7
GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS = 7
GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS = 7
GOOGLE_FIT_PAGE_SIZE_DAYS = 7
GOOGLE_FIT_MAX_SYNC_RETRIES = 2
GOOGLE_FIT_API_REQUEST_RETRIES = 2
GOOGLE_FIT_SYNC_LOCK_TTL_SECONDS = 300
GOOGLE_FIT_SYNC_RATE_LIMIT_SECONDS = 60
GOOGLE_FIT_DAILY_BUCKET_MILLIS = 24 * 60 * 60 * 1000
GLUCOSE_MGDL_PER_MMOLL = 18.0
GLUCOSE_MMOLL_INFERENCE_MAX = 30.0
GOOGLE_FIT_METRIC_DATA_TYPES = {
    "heart_rate": GOOGLE_FIT_HEART_RATE_DATA_TYPE,
    "steps": GOOGLE_FIT_STEP_DATA_TYPE,
    "sleep": GOOGLE_FIT_SLEEP_DATA_TYPE,
    "spo2": GOOGLE_FIT_SPO2_DATA_TYPE,
    "glucose": GOOGLE_FIT_GLUCOSE_DATA_TYPE,
    "blood_pressure": GOOGLE_FIT_BLOOD_PRESSURE_DATA_TYPE,
    "body_temperature": GOOGLE_FIT_BODY_TEMPERATURE_DATA_TYPE,
    "location": GOOGLE_FIT_LOCATION_DATA_TYPE,
}
GOOGLE_FIT_HEART_RATE_SOURCE_PRIORITY = (
    "com.coveiot.android.boat",
    "merge_heart_rate_bpm",
    "resting_heart_rate",
)
GOOGLE_FIT_STEP_SOURCE_PRIORITY = (
    "estimated_steps",
)
GOOGLE_FIT_OPTIONAL_SYNC_METRICS = {"sleep", "spo2", "location"}
GOOGLE_FIT_RECONSENT_METRICS = {"glucose", "blood_pressure", "body_temperature"}
logger = logging.getLogger("google_fit_service")


class BloodPressureFetchResult(list):
    """List-like fetch result that carries BP validation status."""

    def __init__(
        self,
        records: list[dict[str, Any]] | None = None,
        *,
        invalid_duplicate_detected: bool = False,
    ) -> None:
        super().__init__(records or [])
        self.invalid_duplicate_detected = bool(invalid_duplicate_detected)


class GoogleFitService:
    CORE_METRIC_SCOPE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
        "steps": (GOOGLE_FIT_ACTIVITY_SCOPE,),
        "heart_rate": (GOOGLE_FIT_BODY_SCOPE, GOOGLE_FIT_HEART_RATE_SCOPE),
        "sleep": (GOOGLE_FIT_SLEEP_SCOPE,),
        "spo2": (GOOGLE_FIT_OXYGEN_SCOPE,),
        "glucose": (GOOGLE_FIT_BLOOD_GLUCOSE_SCOPE,),
        "blood_pressure": (GOOGLE_FIT_BLOOD_PRESSURE_SCOPE,),
        "body_temperature": (GOOGLE_FIT_BODY_TEMPERATURE_SCOPE,),
        "location": (GOOGLE_FIT_LOCATION_SCOPE,),
    }
    METRIC_VITAL_TYPE_MAP: dict[str, tuple[UserVitalTypeEnum, ...]] = {
        "steps": (UserVitalTypeEnum.STEPS,),
        "heart_rate": (UserVitalTypeEnum.HEART_RATE,),
        "sleep": (UserVitalTypeEnum.SLEEP,),
        "spo2": (UserVitalTypeEnum.SPO2,),
        "glucose": (UserVitalTypeEnum.GLUCOSE,),
        "blood_pressure": (
            UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC,
            UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC,
        ),
        "body_temperature": (UserVitalTypeEnum.BODY_TEMPERATURE,),
    }

    @staticmethod
    def _ensure_configured() -> None:
        if not settings.GOOGLE_FIT_CLIENT_ID or not settings.GOOGLE_FIT_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Fit is not configured on the server",
            )

    @staticmethod
    def _google_fit_verify() -> str | bool:
        if not settings.GOOGLE_FIT_SSL_VERIFY:
            app_env = str(getattr(settings, "APP_ENV", "") or "").strip().lower()
            if app_env in {"dev", "development", "local", "test"}:
                logger.warning("[GFit] SSL verification disabled for Google Fit HTTP client; development fallback only.")
                return False
            logger.warning("[GFit] Ignoring GOOGLE_FIT_SSL_VERIFY=false outside development; SSL verification remains enabled.")

        ca_bundle_candidates = (
            settings.GOOGLE_FIT_CA_BUNDLE,
            os.getenv("SSL_CERT_FILE", ""),
            os.getenv("REQUESTS_CA_BUNDLE", ""),
        )
        for candidate in ca_bundle_candidates:
            if not candidate:
                continue
            ca_bundle = Path(candidate)
            if ca_bundle.is_file():
                return str(ca_bundle)
            logger.warning("[GFit] Configured CA bundle not found; falling back to certifi | path=%s", candidate)

        return certifi.where()

    @staticmethod
    def _log_external_service_failure(
        *,
        operation: str,
        exc: Exception,
        user_id: Any = None,
        retry_count: int = 0,
        fallback_used: bool = True,
    ) -> None:
        logger.error(
            "external_service_failure | service=google_fit | operation=%s | user=%s | retry_count=%s | fallback_used=%s | error_type=%s | error=%s",
            operation,
            user_id,
            retry_count,
            fallback_used,
            exc.__class__.__name__,
            exc,
            exc_info=True,
        )

    @staticmethod
    def build_fault_tolerant_sync_failure_response(
        db: Session,
        user: User | None,
        exc: Exception,
        *,
        timezone_name: str | None = None,
        retry_count: int = 0,
        operation: str = "sync",
        fallback_used: bool = True,
    ) -> dict[str, Any]:
        user_id = getattr(user, "id", None)
        GoogleFitService._log_external_service_failure(
            operation=operation,
            exc=exc,
            user_id=user_id,
            retry_count=retry_count,
            fallback_used=fallback_used,
        )

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name)
        connection = GoogleFitService.get_connection(db, user) if user is not None else None
        sync_timestamp = datetime.now(timezone.utc)
        error_payload = {
            "event": "external_service_failure",
            "service": "google_fit",
            "operation": operation,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            "retry_count": retry_count,
            "fallback_used": fallback_used,
            "failed_at": sync_timestamp.isoformat(),
        }

        data_availability = GoogleFitService._empty_data_availability()
        stats = GoogleFitService._build_stats([])
        scope_status: dict[str, bool] = {}
        missing_scopes: list[str] = []
        last_synced_at = None
        google_email = None

        if user is not None:
            try:
                data_availability = GoogleFitService._data_availability_from_user_vitals(db, user)
            except Exception:
                logger.debug("[GFit] Failed to read local data availability after sync failure", exc_info=True)

        if connection is not None:
            try:
                status_data = GoogleFitService.get_status(db, user, timezone_name=resolved_timezone) if user is not None else {}
                stats = status_data.get("stats", stats)
                data_availability = status_data.get("data_availability", data_availability)
                scope_status = status_data.get("scope_status", scope_status) or {}
                missing_scopes = status_data.get("missing_scopes", missing_scopes) or []
                last_synced_at = status_data.get("last_synced_at")
                google_email = status_data.get("google_email")
            except Exception:
                logger.debug("[GFit] Failed to read Google Fit status after sync failure", exc_info=True)

            try:
                raw_payload = GoogleFitService._connection_raw_payload(connection)
                background_sync = raw_payload.get("background_sync") if isinstance(raw_payload, dict) else None
                if isinstance(background_sync, dict):
                    background_sync.update(
                        {
                            "status": "failed",
                            "failed_at": sync_timestamp.isoformat(),
                            "error": str(exc),
                            "retry_count": retry_count,
                            "fallback_used": fallback_used,
                        }
                    )
                    raw_payload["background_sync"] = background_sync
                raw_payload["external_service_failure"] = error_payload
                connection.raw_last_response = raw_payload
                connection.last_sync_status = "failed"
                db.add(connection)
                db.commit()
                db.refresh(connection)
                last_synced_at = connection.last_synced_at.isoformat() if connection.last_synced_at else last_synced_at
                google_email = connection.google_email
            except Exception:
                db.rollback()
                logger.exception("[GFit] Failed to persist external service failure | user=%s", user_id)

        return {
            "success": True,
            "status": "failed",
            "wearable_status": "failed",
            "message": "Google Fit sync unavailable",
            "core_system": "healthy",
            "error": str(exc),
            "source": "google_fit",
            "partial": True,
            "connected": bool(connection),
            "timezone": resolved_timezone,
            "last_synced_at": last_synced_at,
            "last_sync_status": "failed",
            "stats": stats,
            "raw_json": getattr(connection, "raw_last_response", None) if connection is not None else {"external_service_failure": error_payload},
            "google_email": google_email,
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data_availability": data_availability,
            "scope_status": scope_status,
            "missing_scopes": missing_scopes,
            "needs_reconsent": bool(missing_scopes),
            "retry_count": retry_count,
            "fallback_used": fallback_used,
            "data": [],
        }

    @staticmethod
    async def _google_api_request(
        method: str,
        url: str,
        *,
        operation: str,
        timeout: float,
        **kwargs: Any,
    ) -> httpx.Response:
        verify = GoogleFitService._google_fit_verify()
        last_error: Exception | None = None
        for attempt in range(1, GOOGLE_FIT_API_REQUEST_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
                    response = await client.request(method, url, **kwargs)
                break
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= GOOGLE_FIT_API_REQUEST_RETRIES:
                    logger.exception(
                        "[GFit] Google API transport failure | operation=%s | method=%s | url=%s | verify=%s | attempt=%s/%s | error_type=%s | error=%s",
                        operation,
                        method.upper(),
                        url,
                        verify,
                        attempt,
                        GOOGLE_FIT_API_REQUEST_RETRIES,
                        exc.__class__.__name__,
                        exc,
                    )
                    raise

                logger.warning(
                    "[GFit] Google API transport retry | operation=%s | method=%s | url=%s | verify=%s | attempt=%s/%s | error_type=%s | error=%s",
                    operation,
                    method.upper(),
                    url,
                    verify,
                    attempt,
                    GOOGLE_FIT_API_REQUEST_RETRIES,
                    exc.__class__.__name__,
                    exc,
                )
                await asyncio.sleep(float(attempt))

        if last_error is not None and "response" not in locals():
            raise last_error

        logger.info(
            "[GFit] Google API response | operation=%s | method=%s | status=%s | bytes=%s | success=%s",
            operation,
            method.upper(),
            response.status_code,
            len(response.text or ""),
            not response.is_error,
        )
        return response

    @staticmethod
    def _resolve_timezone(timezone_name: str | None) -> str:
        candidate = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        try:
            ZoneInfo(candidate)
            return candidate
        except Exception:
            fallback = settings.GOOGLE_FIT_DEFAULT_TIMEZONE or "Asia/Kolkata"
            logger.warning("[GFit] Unsupported timezone '%s'; falling back to %s", candidate, fallback)
            return fallback

    @staticmethod
    def _safe_timezone_info(timezone_name: str | None):
        candidate = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE or "Asia/Kolkata"
        try:
            return ZoneInfo(candidate)
        except Exception:
            fallback = settings.GOOGLE_FIT_DEFAULT_TIMEZONE or "Asia/Kolkata"
            logger.warning("[GFit] ZoneInfo unavailable for '%s'; using %s fallback", candidate, fallback)
            try:
                return ZoneInfo(fallback)
            except Exception:
                try:
                    return ZoneInfo("Asia/Kolkata")
                except Exception:
                    return timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

    @staticmethod
    def _coerce_utc_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric > 10_000_000_000:
                numeric /= 1000.0
            try:
                return datetime.fromtimestamp(numeric, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None

        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                return None
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

        return None

    @staticmethod
    def _coerce_millis(value: Any) -> int | None:
        parsed = GoogleFitService._coerce_utc_datetime(value)
        if parsed is None:
            return None
        return int(parsed.astimezone(timezone.utc).timestamp() * 1000)

    @staticmethod
    def _extract_numeric_value(value: Any) -> float | None:
        if not isinstance(value, dict):
            return None

        for key in ("intVal", "fpVal"):
            raw_value = value.get(key)
            if raw_value is None:
                continue
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                continue

        map_values = value.get("mapVal")
        if isinstance(map_values, list):
            numeric_values: list[float] = []
            for item in map_values:
                nested_value = item.get("value") if isinstance(item, dict) else None
                extracted = GoogleFitService._extract_numeric_value(nested_value)
                if extracted is not None:
                    numeric_values.append(extracted)
            if numeric_values:
                return float(sum(numeric_values))

        return None

    @staticmethod
    def _extract_point_values(point: dict[str, Any]) -> list[float]:
        extracted_values: list[float] = []
        for value in point.get("value") or []:
            extracted = GoogleFitService._extract_numeric_value(value)
            if extracted is not None:
                extracted_values.append(extracted)
        return extracted_values

    @staticmethod
    def _extract_direct_numeric_value(value: Any) -> float | None:
        if not isinstance(value, dict):
            return None

        for key in ("intVal", "fpVal"):
            raw_value = value.get(key)
            if raw_value is None:
                continue
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _extract_map_entries(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}

        map_values = value.get("mapVal")
        if isinstance(map_values, dict):
            return {
                str(key).strip().lower(): nested_value
                for key, nested_value in map_values.items()
                if isinstance(key, str)
            }

        if not isinstance(map_values, list):
            return {}

        entries: dict[str, Any] = {}
        for item in map_values:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            nested_value = item.get("value")
            if isinstance(key, str):
                entries[key.strip().lower()] = nested_value
        return entries

    @staticmethod
    def _extract_blood_pressure_numeric(value: Any, *, component: str | None = None) -> float | None:
        map_entries = GoogleFitService._extract_map_entries(value)

        if component:
            if not map_entries:
                return None
            nested_value = map_entries.get(component.strip().lower())
            if nested_value is None:
                return None
            return GoogleFitService._extract_blood_pressure_numeric(nested_value)

        direct_numeric = GoogleFitService._extract_direct_numeric_value(value)
        if direct_numeric is not None:
            return float(direct_numeric)

        if not map_entries:
            return None

        for aggregate_key in ("average", "avg", "mean", "value"):
            nested_value = map_entries.get(aggregate_key)
            if nested_value is None:
                continue
            extracted = GoogleFitService._extract_blood_pressure_numeric(nested_value)
            if extracted is not None:
                return float(extracted)

        if len(map_entries) == 1:
            return GoogleFitService._extract_blood_pressure_numeric(next(iter(map_entries.values())))

        return None

    @staticmethod
    def _extract_blood_pressure_fp_values(values: list[Any]) -> list[float]:
        numeric_values: list[float] = []
        for value in values:
            if not isinstance(value, dict):
                continue
            raw_value = value.get("fpVal")
            if raw_value is None:
                continue
            try:
                numeric_values.append(float(raw_value))
            except (TypeError, ValueError):
                continue
        return numeric_values

    @staticmethod
    def _extract_blood_pressure_pair(
        values: list[Any],
    ) -> tuple[tuple[float, float] | None, str]:
        for value in values:
            systolic = GoogleFitService._extract_blood_pressure_numeric(value, component="systolic")
            diastolic = GoogleFitService._extract_blood_pressure_numeric(value, component="diastolic")
            if systolic is not None and diastolic is not None:
                return (float(systolic), float(diastolic)), "map_values"

        numeric_values = GoogleFitService._extract_blood_pressure_fp_values(values)
        if len(numeric_values) < 2:
            return None, "insufficient_values"

        if len(set(numeric_values)) == 1:
            return None, "duplicate_values"

        systolic_vals = [value for value in numeric_values if value >= 100]
        diastolic_vals = [value for value in numeric_values if value < 100]
        if not systolic_vals or not diastolic_vals:
            return None, "clustering_failed"

        systolic = int(statistics.median(systolic_vals))
        diastolic = int(statistics.median(diastolic_vals))
        logger.info(
            "BP_PARSED_FROM_AGGREGATE_MEDIAN | raw=%s | systolic_vals=%s | diastolic_vals=%s | final=%s/%s",
            numeric_values,
            systolic_vals,
            diastolic_vals,
            systolic,
            diastolic,
        )
        return (float(systolic), float(diastolic)), "aggregate_median"

        return None, "non_numeric_values"

    @staticmethod
    def _parse_blood_pressure_with_reason(datapoint: dict[str, Any]) -> tuple[tuple[float, float] | None, str | None]:
        values = datapoint.get("value") or []
        logger.info("BP_RAW_DATA | stage=google_fit_fetch | values=%s", values)
        parsed_pair, parse_path = GoogleFitService._extract_blood_pressure_pair(values)
        if parsed_pair is None and parse_path == "insufficient_values":
            logger.warning(
                "BP_PARSE_ERROR_INSUFFICIENT_VALUES | values=%s",
                values,
            )
            logger.warning(
                "BP_PARSE_ERROR | reason=insufficient_values | values=%s",
                values,
            )
            logger.warning(
                "BP_SKIPPED_INVALID | reason=insufficient_values | values=%s",
                values,
            )
            logger.warning(
                "BP_VALIDATION | stage=google_fit_parse | status=rejected_missing | systolic=%s | diastolic=%s",
                None,
                None,
            )
            return None, "insufficient_values"

        if parsed_pair is None and parse_path == "clustering_failed":
            numeric_values = GoogleFitService._extract_blood_pressure_fp_values(values)
            logger.warning(
                "BP_CLUSTERING_FAILED | numeric_values=%s",
                numeric_values,
            )
            logger.warning(
                "BP_SKIPPED_INVALID | reason=clustering_failed | values=%s",
                values,
            )
            logger.warning(
                "BP_VALIDATION | stage=google_fit_parse | status=rejected_non_numeric | systolic=%s | diastolic=%s",
                None,
                None,
            )
            return None, "clustering_failed"

        if parsed_pair is None and parse_path == "duplicate_values":
            numeric_values = GoogleFitService._extract_blood_pressure_fp_values(values)
            duplicate_value = numeric_values[0] if numeric_values else None
            logger.warning(
                "BP_DUPLICATE_DETECTED_AFTER_PARSE | systolic=%s | diastolic=%s | values=%s",
                duplicate_value,
                duplicate_value,
                values,
            )
            logger.warning(
                "BP_SKIPPED_INVALID | reason=duplicate_values | systolic=%s | diastolic=%s",
                duplicate_value,
                duplicate_value,
            )
            logger.warning(
                "BP_VALIDATION | stage=google_fit_parse | status=rejected_duplicate | systolic=%s | diastolic=%s",
                duplicate_value,
                duplicate_value,
            )
            return None, "duplicate_values"

        if parsed_pair is None:
            logger.warning(
                "BP_PARSE_ERROR | reason=non_numeric_values | values=%s",
                values,
            )
            logger.warning(
                "BP_SKIPPED_INVALID | reason=non_numeric_values | values=%s",
                values,
            )
            logger.warning(
                "BP_VALIDATION | stage=google_fit_parse | status=rejected_non_numeric | systolic=%s | diastolic=%s",
                None,
                None,
            )
            return None, "non_numeric_values"

        systolic_value, diastolic_value = parsed_pair
        if systolic_value == diastolic_value:
            logger.warning(
                "BP_DUPLICATE_DETECTED_AFTER_PARSE | systolic=%s | diastolic=%s | values=%s",
                systolic_value,
                diastolic_value,
                values,
            )
            logger.warning(
                "BP_SKIPPED_INVALID | reason=duplicate_values | systolic=%s | diastolic=%s",
                systolic_value,
                diastolic_value,
            )
            logger.warning(
                "BP_VALIDATION | stage=google_fit_parse | status=rejected_duplicate | systolic=%s | diastolic=%s",
                systolic_value,
                diastolic_value,
            )
            return None, "duplicate_values"

        logger.info(
            "BP_VALIDATION | stage=google_fit_parse | status=accepted | systolic=%s | diastolic=%s",
            systolic_value,
            diastolic_value,
        )
        logger.info(
            "BP_PARSED_CORRECT | mode=%s | systolic=%s | diastolic=%s",
            parse_path,
            systolic_value,
            diastolic_value,
        )
        return (systolic_value, diastolic_value), None

    @staticmethod
    def parse_blood_pressure(datapoint: dict[str, Any]) -> tuple[float, float] | None:
        parsed, _reason = GoogleFitService._parse_blood_pressure_with_reason(datapoint)
        return parsed

    @staticmethod
    def _redirect_uri() -> str:
        configured_redirect_uri = settings.GOOGLE_FIT_REDIRECT_URI.strip()
        if configured_redirect_uri:
            return configured_redirect_uri
        return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/v1/google-fit/oauth/callback"

    @staticmethod
    def _build_state_token(
        user: User,
        redirect_path: str,
        timezone_name: str,
        onboarding_step: int | None = None,
    ) -> str:
        safe_redirect = redirect_path if redirect_path and redirect_path.startswith("/") else "/device-settings/google-fit"
        payload = {
            "sub": str(user.id),
            "purpose": "google_fit_oauth",
            "redirect_path": safe_redirect,
            "timezone": timezone_name,
            "onboarding_step": onboarding_step,
            "oauth_state": f"onboarding_step_{onboarding_step}" if onboarding_step else None,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def _parse_state_token(state_token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(state_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=400, detail="Invalid Google Fit OAuth state") from exc

        if payload.get("purpose") != "google_fit_oauth" or not payload.get("sub"):
            raise HTTPException(status_code=400, detail="Invalid Google Fit OAuth state")
        return payload

    @staticmethod
    def _get_or_create_device(db: Session, user: User) -> Device:
        connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user.id).first()
        if connection and connection.device_id:
            device = db.query(Device).filter(Device.id == connection.device_id).first()
            if device:
                return device

        device = db.query(Device).filter(Device.user_id == user.id, Device.device_name == "Google Fit").first()
        if device:
            return device

        device = Device(
            user_id=user.id,
            device_type=DeviceTypeEnum.OTHER,
            device_name="Google Fit",
            mac_address=None,
            is_active=True,
        )
        db.add(device)
        db.flush()
        return device

    @staticmethod
    def _get_or_create_user_device(db: Session, user: User, include_inactive: bool = False) -> UserDevice | None:
        user_device = (
            db.query(UserDevice)
            .filter(
                UserDevice.user_id == user.id,
                UserDevice.provider == PROVIDER_GOOGLE_FIT,
            )
            .first()
        )
        if user_device:
            if include_inactive or user_device.is_active:
                return user_device
            return None

        legacy_connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user.id).first()
        if not legacy_connection:
            return None

        user_device = UserDevice(
            user_id=user.id,
            provider=PROVIDER_GOOGLE_FIT,
            access_token=legacy_connection.access_token_encrypted,
            refresh_token=legacy_connection.refresh_token_encrypted,
            token_expiry=legacy_connection.token_expires_at,
            is_active=bool(legacy_connection.last_sync_status != "disconnected"),
        )
        db.add(user_device)
        db.commit()
        db.refresh(user_device)
        return user_device

    @staticmethod
    def _upsert_user_device(db: Session, user: User, access_token: str, refresh_token: str | None, expires_in: int, is_active: bool = True) -> UserDevice:
        # Reuse inactive rows so reconnect flows do not trip the unique (user_id, provider) constraint.
        user_device = GoogleFitService._get_or_create_user_device(db, user, include_inactive=True)
        if not user_device:
            user_device = UserDevice(
                user_id=user.id,
                provider=PROVIDER_GOOGLE_FIT,
            )
            db.add(user_device)

        user_device.access_token = encrypt_secret(access_token)
        if refresh_token:
            user_device.refresh_token = encrypt_secret(refresh_token)
        user_device.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        user_device.is_active = is_active
        db.flush()
        return user_device

    @staticmethod
    def _persist_refreshed_access_token(
        db: Session,
        user_device: UserDevice,
        access_token: str,
        expires_in: int,
        refresh_token: str | None = None,
        connection: GoogleFitConnection | None = None,
    ) -> None:
        encrypted_access_token = encrypt_secret(access_token)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        user_device.access_token = encrypted_access_token
        user_device.token_expiry = token_expiry
        user_device.is_active = True

        encrypted_refresh_token = None
        if refresh_token is not None:
            encrypted_refresh_token = encrypt_secret(refresh_token)
            user_device.refresh_token = encrypted_refresh_token

        if connection is None:
            connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user_device.user_id).first()

        if connection:
            connection.access_token_encrypted = encrypted_access_token
            connection.token_expires_at = token_expiry
            if encrypted_refresh_token is not None:
                connection.refresh_token_encrypted = encrypted_refresh_token

    @staticmethod
    async def _get_valid_user_device_access_token(db: Session, user_device: UserDevice) -> str:
        if user_device.token_expiry and user_device.token_expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
            cached_access_token = decrypt_secret(user_device.access_token)
            if cached_access_token:
                return cached_access_token

        user_device_id = user_device.id
        connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user_device.user_id).first()
        connection_id = getattr(connection, "id", None)
        refresh_token = decrypt_secret(user_device.refresh_token)
        if not refresh_token and connection:
            refresh_token = decrypt_secret(connection.refresh_token_encrypted)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        logger.info("[GFit] TOKEN REFRESH STARTED | user=%s", user_device.user_id)
        db.close()
        response = await GoogleFitService._google_api_request(
            "POST",
            GOOGLE_TOKEN_URL,
            operation="token_refresh",
            timeout=20.0,
            data={
                "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.is_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        expires_in = token_data.get("expires_in") or 3600
        refresh_token = token_data.get("refresh_token") or refresh_token
        refreshed_user_device = db.query(UserDevice).filter(UserDevice.id == user_device_id).first()
        refreshed_connection = (
            db.query(GoogleFitConnection).filter(GoogleFitConnection.id == connection_id).first()
            if connection_id is not None
            else None
        )
        if refreshed_user_device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Google Fit device connection no longer exists.",
            )
        GoogleFitService._persist_refreshed_access_token(
            db,
            refreshed_user_device,
            access_token,
            int(expires_in),
            refresh_token=refresh_token,
            connection=refreshed_connection,
        )
        logger.info("[GFit] TOKEN REFRESHED | user=%s | expires_in=%s", user_device.user_id, expires_in)
        db.commit()
        return access_token

    @staticmethod
    async def get_valid_access_token(db: Session, user: User) -> str | None:
        user_device = GoogleFitService._get_or_create_user_device(db, user)
        if not user_device:
            return None
        return await GoogleFitService._get_valid_user_device_access_token(db, user_device)

    @staticmethod
    async def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
        redirect_uri = GoogleFitService._redirect_uri()
        logger.info(f"[GFit] Token exchange start | redirect_uri={redirect_uri}")

        response = await GoogleFitService._google_api_request(
            "POST",
            GOOGLE_TOKEN_URL,
            operation="token_exchange",
            timeout=20.0,
            data={
                "code": code,
                "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.is_error:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            logger.error(
                f"[GFit] Token exchange FAILED | status={response.status_code} "
                f"| redirect_uri={redirect_uri} | google_response={error_body}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Google token exchange failed: {error_body}",
            )
        return response.json()

    @staticmethod
    async def _fetch_google_email(access_token: str) -> str | None:
        response = await GoogleFitService._google_api_request(
            "GET",
            GOOGLE_USERINFO_URL,
            operation="userinfo",
            timeout=20.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.is_error:
            return None
        return response.json().get("email")

    @staticmethod
    def _build_bucket_window(timezone_name: str, days: int) -> tuple[int, int]:
        return GoogleFitService._build_recent_local_day_series_window(timezone_name, days)

    @staticmethod
    def _millis_to_nanos(value: int) -> int:
        return int(value) * 1_000_000

    @staticmethod
    def _build_rolling_window(days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS) -> tuple[int, int]:
        end = datetime.now(timezone.utc)
        window_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        start = end - timedelta(days=window_days)
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    @staticmethod
    def _build_recent_local_window(timezone_name: str, days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS) -> tuple[int, int]:
        window_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        return GoogleFitService._build_recent_local_day_series_window(timezone_name, window_days)

    @staticmethod
    def _build_local_day_window(timezone_name: str, at: datetime | None = None) -> tuple[str, int, int]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        if at is None:
            now_local = datetime.now(tzinfo)
        else:
            aware_at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
            now_local = aware_at.astimezone(tzinfo)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            now_local.date().isoformat(),
            int(start_local.timestamp() * 1000),
            int(now_local.timestamp() * 1000),
        )

    @staticmethod
    def _build_recent_local_day_series_window(
        timezone_name: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    ) -> tuple[int, int]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        now_local = datetime.now(tzinfo)
        total_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=total_days - 1)
        return (
            int(start_local.astimezone(timezone.utc).timestamp() * 1000),
            int(now_local.astimezone(timezone.utc).timestamp() * 1000),
        )

    @staticmethod
    def _resolve_fetch_window(
        timezone_name: str,
        *,
        start_ts: Any = None,
        end_ts: Any = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    ) -> tuple[int, int]:
        start_millis = GoogleFitService._coerce_millis(start_ts)
        end_millis = GoogleFitService._coerce_millis(end_ts)
        if start_millis is not None and end_millis is not None and start_millis < end_millis:
            return start_millis, end_millis
        return GoogleFitService._build_recent_local_window(
            timezone_name,
            max(1, int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS)),
        )

    @staticmethod
    def _build_paginated_fetch_windows(
        timezone_name: str,
        *,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        page_size_days: int = GOOGLE_FIT_PAGE_SIZE_DAYS,
    ) -> list[tuple[int, int, int, int]]:
        del page_size_days
        total_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        now_local = datetime.now(tzinfo)
        current_day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        windows: list[tuple[int, int, int, int]] = []
        page_number = 1

        for day_offset in range(total_days):
            if day_offset == 0:
                start_local = current_day_start
                end_local = now_local
            else:
                start_local = current_day_start - timedelta(days=day_offset)
                end_local = start_local + timedelta(days=1)

            page_start_millis = int(start_local.astimezone(timezone.utc).timestamp() * 1000)
            page_end_millis = int(end_local.astimezone(timezone.utc).timestamp() * 1000)
            if page_start_millis >= page_end_millis:
                continue
            windows.append((page_start_millis, page_end_millis, 1, page_number))
            page_number += 1

        return windows

    @staticmethod
    def _build_candidate_windows(
        timezone_name: str,
        *,
        start_ts: Any = None,
        end_ts: Any = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    ) -> list[tuple[int, int, int]]:
        primary_days = max(1, int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS))
        if start_ts is not None and end_ts is not None:
            start_millis, end_millis = GoogleFitService._resolve_fetch_window(
                timezone_name,
                start_ts=start_ts,
                end_ts=end_ts,
                days=primary_days,
            )
            return [(start_millis, end_millis, primary_days)]

        candidate_days_list = [primary_days]
        windows: list[tuple[int, int, int]] = []
        seen_days: set[int] = set()
        for candidate_days in candidate_days_list:
            if candidate_days in seen_days:
                continue
            seen_days.add(candidate_days)
            start_millis, end_millis = GoogleFitService._resolve_fetch_window(timezone_name, days=candidate_days)
            windows.append((start_millis, end_millis, candidate_days))
        return windows

    @staticmethod
    def _build_local_day_series(timezone_name: str, start_millis: int, end_millis: int) -> list[str]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        start_local = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc).astimezone(tzinfo).date()
        end_local_dt = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc).astimezone(tzinfo)
        end_local = end_local_dt.date()
        end_is_exclusive_midnight = (
            end_local_dt.hour == 0
            and end_local_dt.minute == 0
            and end_local_dt.second == 0
            and end_local_dt.microsecond == 0
        )
        final_date = end_local - timedelta(days=1) if end_is_exclusive_midnight else end_local

        series: list[str] = []
        cursor = start_local
        while cursor <= final_date:
            series.append(cursor.isoformat())
            cursor += timedelta(days=1)
        return series

    @staticmethod
    def _local_day_bounds_millis(timezone_name: str, day_value: str) -> tuple[int, int]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        try:
            day = datetime.strptime(day_value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            day = datetime.now(tzinfo).date()
        start_local = datetime(day.year, day.month, day.day, tzinfo=tzinfo)
        end_local = start_local + timedelta(days=1)
        return (
            int(start_local.astimezone(timezone.utc).timestamp() * 1000),
            int(end_local.astimezone(timezone.utc).timestamp() * 1000),
        )

    @staticmethod
    def _local_day_metadata(
        timezone_name: str,
        start_millis: int,
        end_millis: int,
    ) -> list[dict[str, Any]]:
        metadata: list[dict[str, Any]] = []
        for day in GoogleFitService._build_local_day_series(timezone_name, start_millis, end_millis):
            day_start_millis, day_end_millis = GoogleFitService._local_day_bounds_millis(timezone_name, day)
            effective_start = max(start_millis, day_start_millis)
            effective_end = min(end_millis, day_end_millis)
            is_partial = effective_start > day_start_millis or effective_end < day_end_millis
            metadata.append(
                {
                    "date": day,
                    "start_millis": day_start_millis,
                    "end_millis": day_end_millis,
                    "effective_start_millis": effective_start,
                    "effective_end_millis": effective_end,
                    "is_partial": is_partial,
                    "included_in_averages": not is_partial,
                }
            )
        return metadata

    @staticmethod
    def _extract_step_count(bucket: dict[str, Any]) -> int | None:
        total = 0.0
        found_value = False
        seen_timed_points: set[tuple[int | None, int | None, tuple[float, ...]]] = set()
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                if not point:
                    continue
                point_values = GoogleFitService._extract_point_values(point)
                if not point_values:
                    continue
                point_start = GoogleFitService._point_time_millis(point, prefer_end_time=False)
                point_end = GoogleFitService._point_time_millis(point, prefer_end_time=True)
                if point_start is not None or point_end is not None:
                    dedupe_key = (point_start, point_end, tuple(float(value) for value in point_values))
                    if dedupe_key in seen_timed_points:
                        continue
                    seen_timed_points.add(dedupe_key)

                found_value = True
                total += sum(point_values)

        if not found_value:
            return None

        return int(round(total))

    @staticmethod
    def _extract_point_value(point: dict[str, Any]) -> float | int | None:
        point_values = GoogleFitService._extract_point_values(point)
        if not point_values:
            return None
        return point_values[0]

    @staticmethod
    def _build_last_24h_window() -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        return int(start.timestamp() * 1000), int(now.timestamp() * 1000)

    @staticmethod
    def _extract_bucket_start_millis(bucket: dict[str, Any]) -> int | None:
        start_value = bucket.get("startTimeMillis")
        if start_value is not None:
            return int(start_value)

        start_nanos = bucket.get("startTimeNanos")
        if start_nanos is not None:
            return int(start_nanos) // 1_000_000

        return None

    @staticmethod
    def _extract_bucket_end_millis(bucket: dict[str, Any]) -> int | None:
        end_value = bucket.get("endTimeMillis")
        if end_value is not None:
            return int(end_value)

        end_nanos = bucket.get("endTimeNanos")
        if end_nanos is not None:
            return int(end_nanos) // 1_000_000

        return None

    @staticmethod
    def _aggregate_bucket_hour_average(bucket: dict[str, Any]) -> float | None:
        values: list[float] = []
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                extracted_values = GoogleFitService._extract_point_values(point)
                if extracted_values:
                    values.extend(float(value) for value in extracted_values)

        if not values:
            return None

        return round(sum(values) / len(values), 1)

    @staticmethod
    def _extract_sleep_intervals(bucket: dict[str, Any]) -> list[tuple[int, int]]:
        sleep_stage_values = {0, 2, 4, 5, 6}
        intervals: list[tuple[int, int]] = []

        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                extracted_values = GoogleFitService._extract_point_values(point)
                stage_raw = extracted_values[0] if extracted_values else None
                stage_value = int(stage_raw) if stage_raw is not None else None

                if stage_value is not None and stage_value not in sleep_stage_values:
                    continue

                start_nanos = point.get("startTimeNanos")
                end_nanos = point.get("endTimeNanos")
                if start_nanos is None or end_nanos is None:
                    continue

                try:
                    start_value = int(start_nanos)
                    end_value = int(end_nanos)
                except (TypeError, ValueError):
                    continue
                if end_value > start_value:
                    intervals.append((start_value, end_value))

        return intervals

    @staticmethod
    def _sleep_hours_from_intervals(intervals: list[tuple[int, int]]) -> float:
        if not intervals:
            return 0.0

        merged: list[tuple[int, int]] = []
        for start_nanos, end_nanos in sorted(intervals):
            if not merged or start_nanos > merged[-1][1]:
                merged.append((start_nanos, end_nanos))
                continue
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end_nanos))

        total_seconds = sum((end_nanos - start_nanos) / 1_000_000_000 for start_nanos, end_nanos in merged)
        return round(total_seconds / 3600.0, 2)

    @staticmethod
    def _aggregate_sleep_hours(bucket: dict[str, Any]) -> float:
        intervals = GoogleFitService._extract_sleep_intervals(bucket)
        return GoogleFitService._sleep_hours_from_intervals(intervals)

    @staticmethod
    def _aggregate_oxygen_average(bucket: dict[str, Any]) -> float | None:
        values: list[float] = []
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                extracted_values = GoogleFitService._extract_point_values(point)
                if extracted_values:
                    values.extend(float(value) for value in extracted_values)

        if not values:
            return None

        return round(sum(values) / len(values), 1)

    @staticmethod
    def _response_point_count(response_json: dict[str, Any]) -> int:
        total_points = 0
        for bucket in response_json.get("bucket", []):
            for dataset in bucket.get("dataset", []):
                total_points += len(dataset.get("point") or [])
        total_points += len(response_json.get("point") or [])
        return total_points

    @staticmethod
    def _raw_dataset_points(response_json: dict[str, Any]) -> list[dict[str, Any]]:
        points = response_json.get("point") if isinstance(response_json, dict) else None
        if not isinstance(points, list):
            return []
        return [point for point in points if isinstance(point, dict)]

    @staticmethod
    def _point_time_millis(point: dict[str, Any], *, prefer_end_time: bool = False) -> int | None:
        keys = ("endTimeNanos", "startTimeNanos") if prefer_end_time else ("startTimeNanos", "endTimeNanos")
        for key in keys:
            raw_value = point.get(key)
            if raw_value is None:
                continue
            try:
                return int(raw_value) // 1_000_000
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _point_overlaps_window(point: dict[str, Any], start_millis: int, end_millis: int) -> bool:
        point_start = GoogleFitService._point_time_millis(point, prefer_end_time=False)
        point_end = GoogleFitService._point_time_millis(point, prefer_end_time=True)
        if point_start is None and point_end is None:
            return False
        if point_end is not None and point_end < start_millis:
            return False
        if point_start is not None and point_start >= end_millis:
            return False
        return True

    @staticmethod
    def _bucket_raw_dataset_response(
        response_json: dict[str, Any],
        *,
        start_millis: int,
        end_millis: int,
        bucket_duration_millis: int,
        prefer_end_time: bool = False,
    ) -> dict[str, Any]:
        if bucket_duration_millis <= 0 or end_millis <= start_millis:
            return {"bucket": [], "raw_dataset_size": 0}

        buckets_by_start: dict[int, dict[str, Any]] = {}
        raw_points = [
            point
            for point in GoogleFitService._raw_dataset_points(response_json)
            if GoogleFitService._point_overlaps_window(point, start_millis, end_millis)
        ]
        for point in raw_points:
            point_millis = GoogleFitService._point_time_millis(point, prefer_end_time=prefer_end_time)
            if point_millis is None:
                continue
            clamped_millis = min(max(point_millis, start_millis), end_millis - 1)
            bucket_index = max(0, (clamped_millis - start_millis) // bucket_duration_millis)
            bucket_start = start_millis + bucket_index * bucket_duration_millis
            bucket_end = min(end_millis, bucket_start + bucket_duration_millis)
            bucket = buckets_by_start.setdefault(
                bucket_start,
                {
                    "startTimeMillis": str(bucket_start),
                    "endTimeMillis": str(bucket_end),
                    "dataset": [{"point": []}],
                },
            )
            bucket["dataset"][0]["point"].append(point)

        return {
            "bucket": [buckets_by_start[key] for key in sorted(buckets_by_start)],
            "raw_dataset_size": len(raw_points),
        }

    @staticmethod
    def _log_raw_google_fit_response(
        metric_name: str,
        response_json: dict[str, Any],
        *,
        start_millis: int | None = None,
        end_millis: int | None = None,
        timezone_name: str | None = None,
        data_source_id: str | None = None,
    ) -> None:
        start_iso = (
            datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc).isoformat()
            if start_millis is not None
            else None
        )
        end_iso = (
            datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc).isoformat()
            if end_millis is not None
            else None
        )
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        bucket_trace: list[dict[str, Any]] = []
        omitted_buckets = 0
        if isinstance(response_json, dict):
            buckets = response_json.get("bucket", [])
            if isinstance(buckets, list):
                omitted_buckets = max(0, len(buckets) - 12)
                for index, bucket in enumerate(buckets[:12]):
                    if not isinstance(bucket, dict):
                        continue
                    bucket_start = GoogleFitService._extract_bucket_start_millis(bucket)
                    bucket_end = GoogleFitService._extract_bucket_end_millis(bucket)
                    raw_values: list[float | int] = []
                    point_count = 0
                    for dataset in bucket.get("dataset", []):
                        if not isinstance(dataset, dict):
                            continue
                        points = dataset.get("point") or []
                        if not isinstance(points, list):
                            continue
                        point_count += len(points)
                        for point in points[:10]:
                            if isinstance(point, dict):
                                raw_values.extend(GoogleFitService._extract_point_values(point))
                    bucket_trace.append(
                        {
                            "index": index,
                            "start_millis": bucket_start,
                            "end_millis": bucket_end,
                            "start_utc": datetime.fromtimestamp(bucket_start / 1000, tz=timezone.utc).isoformat()
                            if bucket_start is not None
                            else None,
                            "end_utc": datetime.fromtimestamp(bucket_end / 1000, tz=timezone.utc).isoformat()
                            if bucket_end is not None
                            else None,
                            "start_local": datetime.fromtimestamp(bucket_start / 1000, tz=timezone.utc)
                            .astimezone(tzinfo)
                            .isoformat()
                            if bucket_start is not None
                            else None,
                            "end_local": datetime.fromtimestamp(bucket_end / 1000, tz=timezone.utc)
                            .astimezone(tzinfo)
                            .isoformat()
                            if bucket_end is not None
                            else None,
                            "point_count": point_count,
                            "values": raw_values[:20],
                            "step_count": GoogleFitService._extract_step_count(bucket)
                            if "step" in metric_name.lower()
                            else None,
                        }
                    )
        logger.info(
            "[GFit] Raw response received | metric=%s | data_source_id=%s | dataset_size=%s | buckets=%s | points=%s | bytes=%s | start=%s | end=%s | timezone=%s | bucket_trace=%s | omitted_buckets=%s",
            metric_name,
            data_source_id or "all_sources",
            GoogleFitService._response_point_count(response_json) if isinstance(response_json, dict) else "unknown",
            len(response_json.get("bucket", [])) if isinstance(response_json, dict) else "unknown",
            GoogleFitService._response_point_count(response_json) if isinstance(response_json, dict) else "unknown",
            len(str(response_json)) if isinstance(response_json, dict) else "unknown",
            start_iso,
            end_iso,
            timezone_name,
            bucket_trace,
            omitted_buckets,
        )

    @staticmethod
    def _scope_status(connection: GoogleFitConnection | None) -> dict[str, bool]:
        if not connection:
            return {metric_name: False for metric_name in GoogleFitService.CORE_METRIC_SCOPE_REQUIREMENTS}
        return {
            metric_name: GoogleFitService._has_any_scope(connection, required_scopes)
            for metric_name, required_scopes in GoogleFitService.CORE_METRIC_SCOPE_REQUIREMENTS.items()
        }

    @staticmethod
    def _missing_metric_scopes(connection: GoogleFitConnection | None) -> list[str]:
        return [
            metric_name
            for metric_name, has_scope in GoogleFitService._scope_status(connection).items()
            if not has_scope
        ]

    @staticmethod
    def _empty_data_availability() -> dict[str, bool]:
        return {metric_name: False for metric_name in GoogleFitService.CORE_METRIC_SCOPE_REQUIREMENTS}

    @staticmethod
    def _metric_vital_types() -> list[UserVitalTypeEnum]:
        vital_types: list[UserVitalTypeEnum] = []
        for mapped_types in GoogleFitService.METRIC_VITAL_TYPE_MAP.values():
            vital_types.extend(mapped_types)
        return vital_types

    @staticmethod
    def _data_availability_from_user_vitals(db: Session, user: User, days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS) -> dict[str, bool]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        availability = GoogleFitService._empty_data_availability()
        rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.timestamp >= cutoff,
                UserVital.vital_type.in_(GoogleFitService._metric_vital_types()),
            )
            .all()
        )
        for row in rows:
            for metric_name, vital_types in GoogleFitService.METRIC_VITAL_TYPE_MAP.items():
                if row.vital_type in vital_types and row.value is not None:
                    availability[metric_name] = True
        return availability

    @staticmethod
    def _count_user_vitals_by_metric(db: Session, user: User, days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS) -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        counts = {metric_name: 0 for metric_name in GoogleFitService.METRIC_VITAL_TYPE_MAP}
        rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.timestamp >= cutoff,
                UserVital.vital_type.in_(GoogleFitService._metric_vital_types()),
            )
            .all()
        )
        for row in rows:
            for metric_name, vital_types in GoogleFitService.METRIC_VITAL_TYPE_MAP.items():
                if row.vital_type in vital_types:
                    counts[metric_name] += 1
        return counts

    @staticmethod
    def _data_source_type_name(source: dict[str, Any]) -> str | None:
        data_type = source.get("dataType") if isinstance(source, dict) else None
        if isinstance(data_type, dict):
            type_name = data_type.get("name")
            return str(type_name) if type_name else None
        return None

    @staticmethod
    def _data_source_id(source: dict[str, Any]) -> str | None:
        for key in ("dataStreamId", "dataSourceId", "id"):
            value = source.get(key) if isinstance(source, dict) else None
            if value:
                return str(value)
        return None

    @staticmethod
    def _data_source_app_name(source: dict[str, Any]) -> str | None:
        application = source.get("application") if isinstance(source, dict) else None
        if isinstance(application, dict):
            for key in ("packageName", "name", "detailsUrl"):
                value = application.get(key)
                if value:
                    return str(value)
        return None

    @staticmethod
    def _data_source_identity(source: dict[str, Any] | None) -> str:
        if not isinstance(source, dict):
            return ""
        parts = [
            GoogleFitService._data_source_id(source),
            GoogleFitService._data_source_app_name(source),
            source.get("dataStreamName"),
            source.get("name"),
            source.get("type"),
        ]
        return " ".join(str(part).lower() for part in parts if part)

    @staticmethod
    def _source_priority_rank(metric_name: str, source: dict[str, Any]) -> tuple[int, str]:
        identity = GoogleFitService._data_source_identity(source)
        if metric_name == "heart_rate":
            for index, marker in enumerate(GOOGLE_FIT_HEART_RATE_SOURCE_PRIORITY):
                if marker in identity:
                    return index, identity
            return len(GOOGLE_FIT_HEART_RATE_SOURCE_PRIORITY), identity

        if metric_name == "steps":
            for index, marker in enumerate(GOOGLE_FIT_STEP_SOURCE_PRIORITY):
                if marker in identity:
                    return index, identity
            return len(GOOGLE_FIT_STEP_SOURCE_PRIORITY), identity

        return 0, identity

    @staticmethod
    def _prioritize_data_sources(metric_name: str, sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for source in sources or []:
            source_id = GoogleFitService._data_source_id(source)
            if source_id and source_id not in deduped:
                deduped[source_id] = source

        prioritized = sorted(
            deduped.values(),
            key=lambda source: GoogleFitService._source_priority_rank(metric_name, source),
        )
        if prioritized:
            logger.info(
                "[GFit] Prioritized %s sources | ids=%s",
                metric_name,
                [GoogleFitService._data_source_id(source) for source in prioritized],
        )
        return prioritized

    @staticmethod
    def _estimated_step_sources(sources: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        for source in sources or []:
            if GoogleFitService._data_source_id(source) == GOOGLE_FIT_DATASOURCE_ID:
                return [source]
        return [
            {
                "dataStreamId": GOOGLE_FIT_DATASOURCE_ID,
                "dataType": {"name": GOOGLE_FIT_STEP_DATA_TYPE},
            }
        ]

    @staticmethod
    def _summarize_step_response(response_json: dict[str, Any], start_millis: int, end_millis: int) -> dict[str, Any]:
        total_steps = 0
        accepted_intervals: list[tuple[int | None, int | None]] = []
        bucket_summaries: list[dict[str, Any]] = []
        raw_values: list[int] = []
        duplicate_or_overlapping_buckets = 0

        for bucket in response_json.get("bucket", []):
            bucket_start = GoogleFitService._extract_bucket_start_millis(bucket)
            bucket_end = GoogleFitService._extract_bucket_end_millis(bucket)
            if bucket_start is not None and bucket_start < start_millis:
                bucket_start = start_millis
            if bucket_end is not None and bucket_end > end_millis:
                bucket_end = end_millis

            overlaps_existing = False
            if bucket_start is not None and bucket_end is not None:
                overlaps_existing = any(
                    existing_start is not None
                    and existing_end is not None
                    and bucket_start < existing_end
                    and bucket_end > existing_start
                    for existing_start, existing_end in accepted_intervals
                )
            elif (bucket_start, bucket_end) in accepted_intervals:
                overlaps_existing = True

            bucket_raw_values: list[int] = []
            bucket_datapoints = 0
            for dataset in bucket.get("dataset", []):
                bucket_datapoints += len(dataset.get("point") or [])
                for point in dataset.get("point", []):
                    for point_value in GoogleFitService._extract_point_values(point):
                        rounded_value = max(0, int(round(point_value)))
                        bucket_raw_values.append(rounded_value)
                        raw_values.append(rounded_value)

            value = GoogleFitService._extract_step_count(bucket)
            if value is None:
                continue
            if overlaps_existing:
                duplicate_or_overlapping_buckets += 1
                logger.warning(
                    "[GFit] Skipping duplicate/overlapping steps bucket | start_ms=%s | end_ms=%s | steps=%s",
                    bucket_start,
                    bucket_end,
                    value,
                )
                continue

            steps = max(0, int(round(value)))
            total_steps += steps
            accepted_intervals.append((bucket_start, bucket_end))
            bucket_summaries.append(
                {
                    "start_millis": bucket_start,
                    "end_millis": bucket_end,
                    "steps": steps,
                    "raw_values": bucket_raw_values,
                    "datapoints": bucket_datapoints,
                }
            )

        return {
            "total_steps": total_steps,
            "bucket_count": len(bucket_summaries),
            "datapoints": GoogleFitService._response_point_count(response_json),
            "raw_values": raw_values,
            "duplicate_or_overlapping_buckets": duplicate_or_overlapping_buckets,
            "buckets": bucket_summaries,
        }

    @staticmethod
    def _normalize_google_fit_record(
        metric_name: str,
        timestamp_millis: int,
        value: float | int,
        *,
        timezone_name: str,
        unit: str,
        **extra: Any,
    ) -> dict[str, Any]:
        payload = {
            "timestamp": datetime.fromtimestamp(timestamp_millis / 1000, tz=timezone.utc),
            "value": value,
            "type": metric_name,
            "unit": unit,
            "source": "google_fit",
            "timezone": timezone_name,
        }
        payload.update(extra)
        return payload

    @staticmethod
    async def _list_data_sources(access_token: str) -> list[dict[str, Any]]:
        response = await GoogleFitService._google_api_request(
            "GET",
            GOOGLE_FIT_DATA_SOURCE_URL,
            operation="list_data_sources",
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            logger.warning(
                "[GFit] Data sources list failed | status=%s | bytes=%s | body=%s",
                response.status_code,
                len(response.text or ""),
                response.text[:500],
            )
            return []

        payload = response.json()
        sources = payload.get("dataSource", []) if isinstance(payload, dict) else []
        if not isinstance(sources, list):
            sources = []

        logger.info(
            "[GFit] Data sources listed | count=%s | bytes=%s",
            len(sources),
            len(response.text or ""),
        )
        for source in sources:
            if not isinstance(source, dict):
                continue
            logger.info(
                "[GFit] Data source | id=%s | data_type=%s | stream_name=%s | source_type=%s | app=%s",
                GoogleFitService._data_source_id(source),
                GoogleFitService._data_source_type_name(source),
                source.get("dataStreamName"),
                source.get("type"),
                GoogleFitService._data_source_app_name(source),
            )
        return [source for source in sources if isinstance(source, dict)]

    @staticmethod
    def _filter_data_sources_by_metric(sources: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        filtered: dict[str, list[dict[str, Any]]] = {metric_name: [] for metric_name in GOOGLE_FIT_METRIC_DATA_TYPES}
        for source in sources:
            source_id = GoogleFitService._data_source_id(source)
            type_name = GoogleFitService._data_source_type_name(source)
            if not source_id:
                continue
            identity = GoogleFitService._data_source_identity(source)
            for metric_name, expected_type in GOOGLE_FIT_METRIC_DATA_TYPES.items():
                if metric_name == "steps":
                    if type_name == expected_type:
                        filtered[metric_name].append(source)
                    continue
                is_priority_heart_rate = metric_name == "heart_rate" and any(
                    marker in identity for marker in GOOGLE_FIT_HEART_RATE_SOURCE_PRIORITY
                )
                if type_name == expected_type or is_priority_heart_rate:
                    filtered[metric_name].append(source)

        logger.info(
            "[GFit] Filtered data sources | counts=%s",
            {metric_name: len(metric_sources) for metric_name, metric_sources in filtered.items()},
        )
        for metric_name, metric_sources in filtered.items():
            logger.info(
                "[GFit] %s sources | ids=%s",
                metric_name,
                [GoogleFitService._data_source_id(source) for source in metric_sources],
            )
        return filtered

    @staticmethod
    async def _aggregate_fit_data(
        access_token: str,
        data_type_name: str,
        start_millis: int,
        end_millis: int,
        bucket_duration_millis: int,
        data_source_id: str | None = None,
        bucket_period: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        aggregate_by: list[dict[str, str]] = []
        aggregate_item = {"dataTypeName": data_type_name}
        if data_source_id:
            aggregate_item["dataSourceId"] = data_source_id
        aggregate_by.append(aggregate_item)
        bucket_by_time: dict[str, Any] = (
            {"period": bucket_period}
            if bucket_period
            else {"durationMillis": bucket_duration_millis}
        )

        logger.info(
            "[GFit] Aggregate request | data_type=%s | data_source_id=%s | start_ms=%s | end_ms=%s | start_ns=%s | end_ns=%s | bucket_ms=%s | bucket_period=%s",
            data_type_name,
            data_source_id,
            start_millis,
            end_millis,
            GoogleFitService._millis_to_nanos(start_millis),
            GoogleFitService._millis_to_nanos(end_millis),
            bucket_duration_millis,
            bucket_period,
        )

        response = await GoogleFitService._google_api_request(
            "POST",
            GOOGLE_FIT_AGGREGATE_URL,
            operation=f"aggregate:{data_type_name}",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "aggregateBy": aggregate_by,
                "bucketByTime": bucket_by_time,
                "startTimeMillis": start_millis,
                "endTimeMillis": end_millis,
            },
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            logger.warning(
                "[GFit] Aggregate request failed | data_type=%s | data_source_id=%s | status=%s | bytes=%s | body=%s",
                data_type_name,
                data_source_id or "all_sources",
                response.status_code,
                len(response.text or ""),
                response.text[:500],
            )
            raise HTTPException(status_code=400, detail=f"Failed to fetch Google Fit data for {data_type_name}")

        payload = response.json()
        logger.info(
            "[GFit] Aggregate response | data_type=%s | data_source_id=%s | points=%s | bytes=%s",
            data_type_name,
            data_source_id or "all_sources",
            GoogleFitService._response_point_count(payload) if isinstance(payload, dict) else "unknown",
            len(response.text or ""),
        )
        return payload

    @staticmethod
    async def _fetch_raw_dataset(
        access_token: str,
        data_source_id: str,
        start_millis: int,
        end_millis: int,
    ) -> dict[str, Any]:
        dataset_id = f"{GoogleFitService._millis_to_nanos(start_millis)}-{GoogleFitService._millis_to_nanos(end_millis)}"
        encoded_source = quote(data_source_id, safe="")
        url = f"{GOOGLE_FIT_DATA_SOURCE_URL}/{encoded_source}/datasets/{dataset_id}"
        logger.info(
            "[GFit] Raw dataset request | data_source_id=%s | dataset_id=%s | start_ms=%s | end_ms=%s",
            data_source_id,
            dataset_id,
            start_millis,
            end_millis,
        )

        response = await GoogleFitService._google_api_request(
            "GET",
            url,
            operation="raw_dataset",
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            logger.warning(
                "[GFit] Raw dataset failed | data_source_id=%s | status=%s | bytes=%s | body=%s",
                data_source_id,
                response.status_code,
                len(response.text or ""),
                response.text[:500],
            )
            raise HTTPException(status_code=400, detail=f"Failed to fetch raw Google Fit data for {data_source_id}")

        payload = response.json()
        logger.info(
            "[GFit] Raw dataset response | data_source_id=%s | dataset_id=%s | dataset_size=%s | bytes=%s",
            data_source_id,
            dataset_id,
            len(GoogleFitService._raw_dataset_points(payload)) if isinstance(payload, dict) else "unknown",
            len(response.text or ""),
        )
        return payload

    @staticmethod
    async def _fetch_source_dataset_with_raw_fallback(
        access_token: str,
        data_type_name: str,
        start_millis: int,
        end_millis: int,
        bucket_duration_millis: int,
        *,
        data_source_id: str,
        metric_name: str,
        timezone_name: str | None = None,
        prefer_end_time: bool = False,
    ) -> dict[str, Any]:
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            data_type_name,
            start_millis,
            end_millis,
            bucket_duration_millis,
            data_source_id=data_source_id,
        )
        if GoogleFitService._response_point_count(response_json) > 0:
            return response_json

        logger.warning(
            "[GFit] Aggregate returned empty; retrying raw dataset | metric=%s | data_source_id=%s | start_ms=%s | end_ms=%s",
            metric_name,
            data_source_id,
            start_millis,
            end_millis,
        )
        raw_response = await GoogleFitService._fetch_raw_dataset(
            access_token,
            data_source_id,
            start_millis,
            end_millis,
        )
        GoogleFitService._log_raw_google_fit_response(
            f"{metric_name}_raw_dataset",
            raw_response,
            start_millis=start_millis,
            end_millis=end_millis,
            timezone_name=timezone_name,
            data_source_id=data_source_id,
        )
        bucketed_response = GoogleFitService._bucket_raw_dataset_response(
            raw_response,
            start_millis=start_millis,
            end_millis=end_millis,
            bucket_duration_millis=bucket_duration_millis,
            prefer_end_time=prefer_end_time,
        )
        logger.info(
            "[GFit] Raw dataset normalized | metric=%s | data_source_id=%s | dataset_size=%s | buckets=%s",
            metric_name,
            data_source_id,
            bucketed_response.get("raw_dataset_size"),
            len(bucketed_response.get("bucket", [])),
        )
        return bucketed_response

    @staticmethod
    async def _list_sessions(
        access_token: str,
        *,
        start_millis: int,
        end_millis: int,
        activity_type: int | None = None,
    ) -> dict[str, Any]:
        params = {
            "startTime": datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "endTime": datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if activity_type is not None:
            params["activityType"] = str(activity_type)

        response = await GoogleFitService._google_api_request(
            "GET",
            GOOGLE_FIT_SESSIONS_URL,
            operation="list_sessions",
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            raise HTTPException(status_code=400, detail="Failed to fetch Google Fit sleep sessions")

        return response.json()

    @staticmethod
    async def _fetch_sleep_segment_details(
        access_token: str,
        *,
        start_millis: int,
        end_millis: int,
    ) -> dict[str, float]:
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            "com.google.sleep.segment",
            start_millis,
            end_millis,
            max(60_000, end_millis - start_millis),
        )

        stage_minutes: dict[str, float] = defaultdict(float)
        for bucket in response_json.get("bucket", []):
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    values = GoogleFitService._extract_point_values(point)
                    stage_value = int(values[0]) if values else None
                    start_nanos = point.get("startTimeNanos")
                    end_nanos = point.get("endTimeNanos")
                    if stage_value is None or start_nanos is None or end_nanos is None:
                        continue

                    duration_minutes = max(0.0, (int(end_nanos) - int(start_nanos)) / 60_000_000_000)
                    if stage_value in {1, 3}:
                        stage_key = "awake"
                    elif stage_value == 4:
                        stage_key = "light"
                    elif stage_value == 5:
                        stage_key = "deep"
                    elif stage_value == 6:
                        stage_key = "rem"
                    elif stage_value in {0, 2}:
                        stage_key = "sleep"
                    else:
                        continue

                    stage_minutes[stage_key] += duration_minutes

        return {key: round(value, 2) for key, value in stage_minutes.items()}

    @staticmethod
    def _extract_heart_rate_value(bucket: dict[str, Any]) -> float | None:
        values: list[float] = []

        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                extracted_values = GoogleFitService._extract_point_values(point)
                if extracted_values:
                    values.extend(float(value) for value in extracted_values)

        if not values:
            return None

        return round(sum(values) / len(values), 1)

    @staticmethod
    def normalize_heart_rate_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for bucket in payload.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            heart_rate = GoogleFitService._extract_heart_rate_value(bucket)

            if timestamp is None or heart_rate is None:
                continue

            normalized.append(
                GoogleFitService._normalize_google_fit_record(
                    UserVitalTypeEnum.HEART_RATE.value,
                    timestamp,
                    heart_rate,
                    timezone_name=settings.GOOGLE_FIT_DEFAULT_TIMEZONE,
                    unit="bpm",
                )
            )

        return sorted(normalized, key=lambda item: item["timestamp"])

    @staticmethod
    async def _fetch_heart_rate_payload(access_token: str, timezone_name: str | None = None) -> dict[str, Any]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        start_millis, end_millis = GoogleFitService._build_bucket_window(timezone_name, 1)

        response = await GoogleFitService._google_api_request(
            "POST",
            GOOGLE_FIT_AGGREGATE_URL,
            operation="heart_rate_payload",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
                "bucketByTime": {"durationMillis": 3600000},
                "startTimeMillis": start_millis,
                "endTimeMillis": end_millis,
            },
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            raise HTTPException(status_code=400, detail="Failed to fetch Google Fit heart rate")

        return response.json()

    @staticmethod
    def _daily_payload_from_vital_rows(
        rows: list[UserVital],
        timezone_name: str,
        start_millis: int,
        end_millis: int,
    ) -> list[dict[str, Any]]:
        del start_millis, end_millis
        return compute_daily_steps(rows, timezone_name)

    @staticmethod
    def _build_stats(daily_steps: list[dict[str, Any]], timezone_name: str | None = None) -> dict[str, Any]:
        summary = compute_daily_step_summary(daily_steps or [], timezone_name)
        active_days = [item for item in summary["daily_steps"] if int(item["steps"]) > 0]
        today = None
        if timezone_name:
            today = datetime.now(GoogleFitService._safe_timezone_info(timezone_name)).date().isoformat()
        current_day = next(
            (item for item in summary["daily_steps"] if item["date"] == today),
            summary["latest_day"],
        )
        return {
            **summary,
            "total_steps_including_partial": summary["total_steps"],
            "average_daily_steps": summary["average_steps"],
            "average_steps_on_active_days": round(sum(int(item["steps"]) for item in active_days) / len(active_days)) if active_days else 0,
            "latest_complete_day": summary["latest_day"],
            "current_day": current_day,
            "partial_day": None,
            "active_day_count": len(active_days),
            "valid_day_count": len(summary["daily_steps"]),
            "partial_day_count": 0,
        }

    @staticmethod
    def _build_frontend_redirect(redirect_path: str, status_value: str, message: str | None = None) -> str:
        target = f"{settings.FRONTEND_APP_URL.rstrip('/')}{redirect_path}"
        params = {"googleFit": status_value}
        if status_value == "connected":
            params["connected"] = "google_fit"
        if message:
            params["message"] = message
        return f"{target}?{urlencode(params)}"

    @staticmethod
    def _has_scope(connection: GoogleFitConnection, scope: str) -> bool:
        granted_scopes = (connection.scopes or "").split()
        return scope in granted_scopes

    @staticmethod
    def _has_any_scope(connection: GoogleFitConnection, scopes: tuple[str, ...] | list[str] | set[str]) -> bool:
        granted_scopes = set((connection.scopes or "").split())
        return any(scope in granted_scopes for scope in scopes)

    @staticmethod
    def get_connection(db: Session, user: User) -> GoogleFitConnection | None:
        return db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user.id).first()

    @staticmethod
    def get_status(db: Session, user: User, timezone_name: str | None = None) -> dict[str, Any]:
        timezone_name = GoogleFitService._resolve_timezone(timezone_name)
        connection = GoogleFitService.get_connection(db, user)
        data_availability = GoogleFitService._data_availability_from_user_vitals(db, user)
        if not connection:
            return {
                "connected": False,
                "timezone": timezone_name,
                "last_synced_at": None,
                "stats": GoogleFitService._build_stats([]),
                "raw_json": None,
                "google_email": None,
                "data_availability": data_availability,
                "scope_status": GoogleFitService._scope_status(connection),
                "missing_scopes": [],
                "needs_reconsent": False,
            }

        scope_status = GoogleFitService._scope_status(connection)
        missing_scopes = GoogleFitService._missing_metric_scopes(connection)

        has_valid_tokens = bool(connection.access_token_encrypted or connection.refresh_token_encrypted)
        is_explicitly_disconnected = (connection.last_sync_status or "").lower() == "disconnected"
        if not has_valid_tokens or is_explicitly_disconnected:
            return {
                "connected": False,
                "timezone": GoogleFitService._resolve_timezone(connection.default_timezone or timezone_name),
                "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
                "stats": GoogleFitService._build_stats([]),
                "raw_json": connection.raw_last_response,
                "google_email": connection.google_email,
                "last_sync_status": connection.last_sync_status,
                "data_availability": data_availability,
                "scope_status": scope_status,
                "missing_scopes": missing_scopes,
                "needs_reconsent": bool(missing_scopes),
            }

        effective_timezone = GoogleFitService._resolve_timezone(connection.default_timezone or timezone_name)
        start_millis, end_millis = GoogleFitService._build_recent_local_day_series_window(effective_timezone)
        step_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.STEPS,
                UserVital.timestamp >= datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc),
                UserVital.timestamp < datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc),
            )
            .order_by(UserVital.timestamp.asc())
            .all()
        )
        daily_steps = compute_daily_steps(step_rows, effective_timezone)
        return {
            "connected": True,
            "timezone": effective_timezone,
            "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
            "stats": GoogleFitService._build_stats(daily_steps, effective_timezone),
            "raw_json": connection.raw_last_response,
            "google_email": connection.google_email,
            "last_sync_status": connection.last_sync_status,
            "data_availability": data_availability,
            "scope_status": scope_status,
            "missing_scopes": missing_scopes,
            "needs_reconsent": bool(missing_scopes),
        }

    @staticmethod
    async def debug_steps(db: Session, user: User, timezone_name: str | None = None) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or getattr(connection, "default_timezone", None))
        local_day, start_millis, end_millis = GoogleFitService._build_current_local_day_window(resolved_timezone)

        if not connection:
            return {
                "connected": False,
                "timezone": resolved_timezone,
                "message": "Google Fit is not connected",
                "raw_api_response": None,
                "processed_values": None,
                "stored_values": GoogleFitService._stored_step_values_payload(
                    db,
                    user,
                    timezone_name=resolved_timezone,
                    start_millis=start_millis,
                    end_millis=end_millis,
                ),
            }

        access_token = await GoogleFitService.get_valid_access_token(db, user)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        raw_api_response = await GoogleFitService._aggregate_fit_data(
            access_token,
            GOOGLE_FIT_STEP_DATA_TYPE,
            start_millis,
            end_millis,
            GOOGLE_FIT_DAILY_BUCKET_MILLIS,
            data_source_id=GOOGLE_FIT_DATASOURCE_ID,
            bucket_period={"type": "day", "value": 1, "timeZoneId": resolved_timezone},
        )
        step_summary = GoogleFitService._summarize_step_response(raw_api_response, start_millis, end_millis)
        stored_values = GoogleFitService._stored_step_values_payload(
            db,
            user,
            timezone_name=resolved_timezone,
            start_millis=start_millis,
            end_millis=end_millis,
        )

        processed_values = {
            "total_steps": int(step_summary["total_steps"]),
            "datapoints": int(step_summary["datapoints"]),
            "bucket_count": int(step_summary["bucket_count"]),
            "raw_values": step_summary["raw_values"],
            "buckets": step_summary["buckets"],
            "duplicate_or_overlapping_buckets": int(step_summary["duplicate_or_overlapping_buckets"]),
        }
        logger.info(
            "[GFit] Debug steps | user=%s | api_steps=%s | datapoints=%s | stored_steps=%s | local_day=%s",
            user.id,
            processed_values["total_steps"],
            processed_values["datapoints"],
            stored_values["user_vitals_total"],
            local_day,
        )
        return {
            "connected": True,
            "timezone": resolved_timezone,
            "local_day": local_day,
            "request": {
                "url": GOOGLE_FIT_AGGREGATE_URL,
                "aggregateBy": [
                    {
                        "dataTypeName": GOOGLE_FIT_STEP_DATA_TYPE,
                        "dataSourceId": GOOGLE_FIT_DATASOURCE_ID,
                    }
                ],
                "bucketByTime": {"durationMillis": GOOGLE_FIT_DAILY_BUCKET_MILLIS},
                "startTimeMillis": start_millis,
                "endTimeMillis": end_millis,
            },
            "raw_api_response": raw_api_response,
            "processed_values": processed_values,
            "stored_values": stored_values,
            "last_sync_debug": GoogleFitService._connection_raw_payload(connection).get("debug"),
        }

    @staticmethod
    def _connection_raw_payload(connection: GoogleFitConnection | None) -> dict[str, Any]:
        raw_payload = connection.raw_last_response if connection else None
        return dict(raw_payload) if isinstance(raw_payload, dict) else {}

    @staticmethod
    def _step_debug_payload(
        db: Session,
        user: User,
        step_records: list[dict[str, Any]],
        daily_steps_by_day: dict[str, int],
        *,
        timezone_name: str,
        start_millis: int,
        end_millis: int,
    ) -> dict[str, Any]:
        start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
        end_dt_utc = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc)
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        db_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.STEPS,
                UserVital.source == UserVitalSourceEnum.GOOGLE_FIT,
                UserVital.timestamp >= start_dt_utc,
                UserVital.timestamp < end_dt_utc,
            )
            .order_by(UserVital.timestamp.asc())
            .all()
        )

        def _safe_int(value: Any) -> int | None:
            try:
                return max(0, int(round(float(value))))
            except (TypeError, ValueError):
                return None

        raw_steps = None
        processed_steps = None
        source_used = GOOGLE_FIT_DATASOURCE_ID
        datapoints = 0
        bucket_count = 0
        duplicate_or_overlapping_buckets = 0
        if step_records:
            raw_steps = sum(
                value
                for value in (_safe_int(record.get("raw_google_fit_steps", record.get("value"))) for record in step_records)
                if value is not None
            )
            processed_steps = sum(
                value
                for value in (_safe_int(record.get("processed_steps", record.get("value"))) for record in step_records)
                if value is not None
            )
            source_used = str(step_records[0].get("source_used") or source_used)
            datapoints = sum(int(record.get("datapoints") or 0) for record in step_records)
            bucket_count = sum(int(record.get("bucket_count") or 0) for record in step_records)
            duplicate_or_overlapping_buckets = sum(
                int(record.get("duplicate_or_overlapping_buckets") or 0) for record in step_records
            )

        db_steps = sum(
            value
            for value in (_safe_int(getattr(row, "value", None)) for row in db_rows)
            if value is not None
        )
        if processed_steps is None and daily_steps_by_day:
            processed_steps = sum(max(0, int(value)) for value in daily_steps_by_day.values())

        payload = {
            "raw_google_fit_steps": raw_steps,
            "processed_steps": processed_steps,
            "db_steps": db_steps,
            "source_used": source_used,
            "datapoints": datapoints,
            "bucket_count": bucket_count,
            "duplicate_or_overlapping_buckets": duplicate_or_overlapping_buckets,
            "db_row_count": len(db_rows),
            "time_range": {
                "start_millis": start_millis,
                "end_millis": end_millis,
                "start": start_dt_utc.isoformat(),
                "end": end_dt_utc.isoformat(),
                "start_local": start_dt_utc.astimezone(tzinfo).isoformat(),
                "end_local": end_dt_utc.astimezone(tzinfo).isoformat(),
                "timezone": timezone_name,
            },
        }
        logger.info(
            "[GFit] Step debug | user=%s | raw_google_fit_steps=%s | processed_steps=%s | db_steps=%s | source=%s | datapoints=%s | range=%s..%s | timezone=%s",
            user.id,
            payload["raw_google_fit_steps"],
            payload["processed_steps"],
            payload["db_steps"],
            payload["source_used"],
            payload["datapoints"],
            payload["time_range"]["start_local"],
            payload["time_range"]["end_local"],
            timezone_name,
        )
        return payload

    @staticmethod
    def _stored_step_totals_by_day(
        db: Session,
        user: User,
        *,
        timezone_name: str,
        start_millis: int,
        end_millis: int,
    ) -> dict[str, int]:
        start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
        end_dt_utc = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc)
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.STEPS,
                UserVital.source == UserVitalSourceEnum.GOOGLE_FIT,
                UserVital.timestamp >= start_dt_utc,
                UserVital.timestamp < end_dt_utc,
            )
            .all()
        )
        totals: dict[str, int] = {}
        for row in rows:
            if row.timestamp is None or row.value is None:
                continue
            day = row.timestamp.astimezone(tzinfo).date().isoformat()
            try:
                totals[day] = totals.get(day, 0) + max(0, int(round(float(row.value))))
            except (TypeError, ValueError):
                continue
        return totals

    @staticmethod
    def _stored_step_values_payload(
        db: Session,
        user: User,
        *,
        timezone_name: str,
        start_millis: int,
        end_millis: int,
    ) -> dict[str, Any]:
        start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
        end_dt_utc = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc)
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        vital_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.STEPS,
                UserVital.source == UserVitalSourceEnum.GOOGLE_FIT,
                UserVital.timestamp >= start_dt_utc,
                UserVital.timestamp < end_dt_utc,
            )
            .order_by(UserVital.timestamp.asc())
            .all()
        )
        def _safe_int(value: Any) -> int:
            try:
                return max(0, int(round(float(value))))
            except (TypeError, ValueError):
                return 0

        user_vitals = [
            {
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "local_day": row.timestamp.astimezone(tzinfo).date().isoformat() if row.timestamp else None,
                "value": _safe_int(row.value),
                "unit": row.unit,
            }
            for row in vital_rows
        ]
        return {
            "user_vitals_total": sum(item["value"] for item in user_vitals),
            "user_vitals_count": len(user_vitals),
            "user_vitals": user_vitals,
        }

    @staticmethod
    def _filter_delayed_step_records(
        step_records: list[dict[str, Any]],
        existing_steps_by_day: dict[str, int],
        *,
        timezone_name: str,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
        if not step_records or not existing_steps_by_day:
            return step_records, {}

        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        new_steps_by_day: dict[str, int] = defaultdict(int)
        record_days: list[tuple[dict[str, Any], str | None]] = []
        for record in step_records:
            timestamp = record.get("timestamp")
            if not isinstance(timestamp, datetime):
                record_days.append((record, None))
                continue
            day = timestamp.astimezone(tzinfo).date().isoformat()
            record_days.append((record, day))
            try:
                new_steps_by_day[day] += max(0, int(round(float(record.get("value") or 0))))
            except (TypeError, ValueError):
                continue

        delayed_days: dict[str, dict[str, int]] = {}
        for day, api_steps in new_steps_by_day.items():
            existing_steps = max(0, int(existing_steps_by_day.get(day) or 0))
            if existing_steps > 0 and api_steps < existing_steps:
                delayed_days[day] = {
                    "api_steps": int(api_steps),
                    "stored_steps": int(existing_steps),
                }

        if not delayed_days:
            return step_records, {}

        filtered = [record for record, day in record_days if day not in delayed_days]
        return filtered, delayed_days

    @staticmethod
    def get_recent_background_sync(
        db: Session,
        user: User,
        *,
        max_age_seconds: int = 180,
    ) -> dict[str, Any] | None:
        connection = GoogleFitService.get_connection(db, user)
        if not connection or (connection.last_sync_status or "").lower() != "syncing":
            return None

        raw_payload = GoogleFitService._connection_raw_payload(connection)
        background_sync = raw_payload.get("background_sync")
        if not isinstance(background_sync, dict):
            return None

        queued_at = GoogleFitService._coerce_utc_datetime(background_sync.get("queued_at"))
        if queued_at is None:
            return None

        if (datetime.now(timezone.utc) - queued_at).total_seconds() > max_age_seconds:
            return None

        return background_sync

    @staticmethod
    def _redis_client():
        from core.celery_app import CELERY_BROKER_URL
        import redis

        return redis.Redis.from_url(CELERY_BROKER_URL.replace("/0", "/2"), decode_responses=True)

    @staticmethod
    def _sync_lock_key(user_id: str) -> str:
        return f"gfit_sync_lock:{user_id}"

    @staticmethod
    def _sync_rate_limit_key(user_id: str) -> str:
        return f"gfit_sync_rate:{user_id}"

    @staticmethod
    def acquire_sync_lock(user_id: str, ttl_seconds: int = GOOGLE_FIT_SYNC_LOCK_TTL_SECONDS) -> bool:
        try:
            acquired = GoogleFitService._redis_client().set(
                GoogleFitService._sync_lock_key(user_id),
                "1",
                nx=True,
                ex=ttl_seconds,
            )
            return bool(acquired)
        except Exception as exc:
            logger.error("SYNC_ABORTED | user=%s | reason=redis_lock_unavailable | error=%s", user_id, exc)
            return False

    @staticmethod
    def release_sync_lock(user_id: str) -> None:
        try:
            GoogleFitService._redis_client().delete(GoogleFitService._sync_lock_key(user_id))
        except Exception as exc:
            logger.warning("[GFit] Redis lock release failed | user=%s | error=%s", user_id, exc)

    @staticmethod
    def is_sync_locked(user_id: str) -> bool:
        try:
            return bool(GoogleFitService._redis_client().exists(GoogleFitService._sync_lock_key(user_id)))
        except Exception as exc:
            logger.warning("[GFit] Redis lock check failed | user=%s | error=%s", user_id, exc)
            return False

    @staticmethod
    def acquire_sync_rate_limit(user_id: str, ttl_seconds: int = GOOGLE_FIT_SYNC_RATE_LIMIT_SECONDS) -> bool:
        try:
            acquired = GoogleFitService._redis_client().set(
                GoogleFitService._sync_rate_limit_key(user_id),
                "1",
                nx=True,
                ex=ttl_seconds,
            )
            return bool(acquired)
        except Exception as exc:
            logger.warning("[GFit] Redis rate-limit check failed; allowing guarded sync | user=%s | error=%s", user_id, exc)
            return True

    @staticmethod
    def clear_sync_controls(user_id: str) -> None:
        try:
            GoogleFitService._redis_client().delete(
                GoogleFitService._sync_lock_key(user_id),
                GoogleFitService._sync_rate_limit_key(user_id),
                f"gfit_sync_cancel:{user_id}",
            )
        except Exception as exc:
            logger.warning("[GFit] Failed to clear sync controls | user=%s | error=%s", user_id, exc)

    @staticmethod
    def build_sync_blocked_response(
        db: Session,
        user: User,
        *,
        reason: str,
        message: str,
        timezone_name: str | None = None,
        connected: bool = False,
        status_value: str = "auth_blocked",
    ) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or getattr(connection, "default_timezone", None))
        stats = GoogleFitService._build_stats([])
        data_availability = GoogleFitService._empty_data_availability()
        scope_status = GoogleFitService._scope_status(connection)
        missing_scopes: list[str] = []

        if connection is not None:
            try:
                data_availability = GoogleFitService._data_availability_from_user_vitals(db, user)
                missing_scopes = GoogleFitService._missing_metric_scopes(connection)
                raw_payload = GoogleFitService._connection_raw_payload(connection)
                raw_payload["sync_blocked"] = {
                    "reason": reason,
                    "blocked_at": datetime.now(timezone.utc).isoformat(),
                }
                connection.raw_last_response = raw_payload
                if reason in {"token_expired", "tokens_missing", "disconnected"}:
                    if reason in {"token_expired", "tokens_missing"}:
                        connection.access_token_encrypted = None
                        connection.refresh_token_encrypted = None
                    connection.last_sync_status = "auth_failed" if reason != "disconnected" else "disconnected"
                db.add(connection)
                if reason in {"token_expired", "tokens_missing"}:
                    user_device = db.query(UserDevice).filter(
                        UserDevice.user_id == user.id,
                        UserDevice.provider == PROVIDER_GOOGLE_FIT,
                    ).first()
                    if user_device:
                        user_device.access_token = None
                        user_device.refresh_token = None
                        user_device.token_expiry = None
                        user_device.is_active = False
                db.commit()
                db.refresh(connection)
            except Exception:
                db.rollback()
                logger.exception("[GFit] Failed to persist sync blocked state | user=%s | reason=%s", user.id, reason)

        return {
            "success": True,
            "status": status_value,
            "wearable_status": "auth_blocked",
            "core_system": "healthy",
            "error": None,
            "partial": True,
            "message": message,
            "source": "google_fit",
            "connected": connected and connection is not None,
            "sync_blocked": True,
            "sync_blocked_reason": reason,
            "data": [],
            "stats": stats,
            "raw_json": getattr(connection, "raw_last_response", None) if connection else None,
            "google_email": getattr(connection, "google_email", None) if connection else None,
            "last_synced_at": connection.last_synced_at.isoformat() if connection and connection.last_synced_at else None,
            "last_sync_status": getattr(connection, "last_sync_status", None) if connection else "disconnected",
            "timezone": resolved_timezone,
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data_availability": data_availability,
            "scope_status": scope_status,
            "missing_scopes": missing_scopes,
            "needs_reconsent": bool(missing_scopes),
        }

    @staticmethod
    async def validate_sync_auth(
        db: Session,
        user: User,
        *,
        timezone_name: str | None = None,
        sync_mode: str = "sync",
    ) -> tuple[GoogleFitConnection | None, str | None, dict[str, Any] | None]:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=%s | reason=not_connected", user.id, sync_mode)
            return None, None, GoogleFitService.build_sync_blocked_response(
                db,
                user,
                reason="not_connected",
                message="Google Fit is not connected",
                timezone_name=timezone_name,
                connected=False,
                status_value="not_connected",
            )

        if (connection.last_sync_status or "").lower() == "disconnected":
            logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=%s | reason=disconnected", user.id, sync_mode)
            return connection, None, GoogleFitService.build_sync_blocked_response(
                db,
                user,
                reason="disconnected",
                message="Google Fit is disconnected",
                timezone_name=timezone_name,
                connected=False,
                status_value="not_connected",
            )

        if not connection.access_token_encrypted and not connection.refresh_token_encrypted:
            logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=%s | reason=tokens_missing", user.id, sync_mode)
            return connection, None, GoogleFitService.build_sync_blocked_response(
                db,
                user,
                reason="tokens_missing",
                message="Google Fit authorization expired. Please reconnect Google Fit.",
                timezone_name=timezone_name,
                connected=True,
            )

        try:
            access_token = await GoogleFitService.get_valid_access_token(db, user)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=%s | reason=token_expired", user.id, sync_mode)
                return connection, None, GoogleFitService.build_sync_blocked_response(
                    db,
                    user,
                    reason="token_expired",
                    message="Google Fit authorization expired. Please reconnect Google Fit.",
                    timezone_name=timezone_name,
                    connected=True,
                )
            raise

        if not access_token:
            logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=%s | reason=token_expired", user.id, sync_mode)
            return connection, None, GoogleFitService.build_sync_blocked_response(
                db,
                user,
                reason="token_expired",
                message="Google Fit authorization expired. Please reconnect Google Fit.",
                timezone_name=timezone_name,
                connected=True,
            )

        return connection, access_token, None

    @staticmethod
    def mark_background_sync_queued(
        db: Session,
        user: User,
        *,
        task_id: str | None,
        timezone_name: str | None = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        initial_window_days: int = GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS,
    ) -> GoogleFitConnection | None:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            return None

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or connection.default_timezone)
        requested_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        queued_at = datetime.now(timezone.utc)
        raw_payload = GoogleFitService._connection_raw_payload(connection)
        raw_payload["background_sync"] = {
            "task_id": task_id,
            "status": "queued",
            "queued_at": queued_at.isoformat(),
            "requested_days": requested_days,
            "initial_window_days": min(initial_window_days, requested_days),
            "max_retries": GOOGLE_FIT_MAX_SYNC_RETRIES,
        }

        connection.default_timezone = resolved_timezone
        connection.last_sync_status = "syncing"
        connection.raw_last_response = raw_payload
        db.add(connection)
        db.commit()
        db.refresh(connection)
        return connection

    @staticmethod
    def build_background_sync_response(
        db: Session,
        user: User,
        *,
        timezone_name: str | None = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        task_id: str | None = None,
        already_running: bool = False,
    ) -> dict[str, Any]:
        status_data = GoogleFitService.get_status(db, user, timezone_name=timezone_name)
        requested_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        message = (
            "Google Fit sync is already running in the background."
            if already_running
            else "Google Fit sync started. Recent data will update in the background."
        )
        raw_payload = status_data.get("raw_json") if isinstance(status_data.get("raw_json"), dict) else {}
        background_sync = raw_payload.get("background_sync") if isinstance(raw_payload, dict) else None

        return {
            "success": True,
            "status": "queued",
            "error": None,
            "partial": False,
            "message": message,
            "connected": status_data.get("connected", True),
            "sync_mode": "background",
            "task_id": task_id or (background_sync or {}).get("task_id"),
            "requested_days": requested_days,
            "initial_window_days": min(GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS, requested_days),
            "max_retries": GOOGLE_FIT_MAX_SYNC_RETRIES,
            "timezone": status_data.get("timezone"),
            "last_synced_at": status_data.get("last_synced_at"),
            "last_sync_status": "syncing",
            "stats": status_data.get("stats", GoogleFitService._build_stats([])),
            "raw_json": status_data.get("raw_json"),
            "google_email": status_data.get("google_email"),
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data_availability": status_data.get("data_availability"),
            "scope_status": status_data.get("scope_status"),
            "missing_scopes": status_data.get("missing_scopes") or [],
            "needs_reconsent": status_data.get("needs_reconsent", False),
            "data": [],
        }

    @staticmethod
    def _log_sync_execution_time(
        user_id: Any,
        start_time: datetime,
        start_perf: float,
        *,
        status_value: str,
    ) -> None:
        end_time = datetime.now(timezone.utc)
        logger.info(
            "[GFit] Sync execution time | user=%s | status=%s | start_time=%s | end_time=%s | duration=%.3fs",
            user_id,
            status_value,
            start_time.isoformat(),
            end_time.isoformat(),
            time.perf_counter() - start_perf,
        )

    @staticmethod
    def build_connect_url(
        user: User,
        timezone_name: str | None = None,
        redirect_path: str | None = None,
        onboarding_step: int | None = None,
    ) -> dict[str, Any]:
        GoogleFitService._ensure_configured()
        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name)
        redirect_uri = GoogleFitService._redirect_uri()
        scopes = " ".join(GOOGLE_FIT_SCOPE_SET)
        state = GoogleFitService._build_state_token(
            user=user,
            redirect_path=redirect_path or "/device-settings/google-fit",
            timezone_name=resolved_timezone,
            onboarding_step=onboarding_step,
        )
        query_params = {
            "client_id": settings.GOOGLE_FIT_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        query = urlencode(query_params, quote_via=quote, safe="")
        auth_url = f"{GOOGLE_AUTH_URL}?{query}"
        logger.info(
            "[GFit] OAuth init | client_id=%s | redirect_uri=%s | scopes=%s | state=%s | onboarding_step=%s",
            settings.GOOGLE_FIT_CLIENT_ID,
            redirect_uri,
            scopes,
            state,
            onboarding_step,
        )
        logger.info("[GFit] OAuth URL: %s", auth_url)
        return {
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "timezone": resolved_timezone,
            "client_id": settings.GOOGLE_FIT_CLIENT_ID,
            "scopes": scopes,
            "state": state,
            "oauth_state": f"onboarding_step_{onboarding_step}" if onboarding_step else None,
        }

    @staticmethod
    def _fetch_window_for_user(user: User, fallback_days: int = 1, timezone_name: str | None = None) -> tuple[str, int, int]:
        del user
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        start_millis, end_millis = GoogleFitService._build_bucket_window(timezone_name, max(1, fallback_days))
        return timezone_name, start_millis, end_millis

    @staticmethod
    def _fetch_local_bucket_window_for_user(
        user: User,
        fallback_days: int = 1,
        timezone_name: str | None = None,
    ) -> tuple[str, int, int]:
        del user
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        start_millis, end_millis = GoogleFitService._build_bucket_window(timezone_name, max(1, fallback_days))
        return timezone_name, start_millis, end_millis

    @staticmethod
    def _build_current_local_day_window(timezone_name: str) -> tuple[str, int, int]:
        return GoogleFitService._build_local_day_window(timezone_name)

    @staticmethod
    async def _fetch_realtime_today_steps(
        access_token: str,
        timezone_name: str,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        local_day, start_millis, end_millis = GoogleFitService._build_current_local_day_window(timezone_name)

        source_totals: list[dict[str, Any]] = []
        fallback_sources = GoogleFitService._estimated_step_sources(data_sources)
        for source in fallback_sources:
            source_id = GoogleFitService._data_source_id(source)
            if not source_id:
                continue
            try:
                source_response = await GoogleFitService._aggregate_fit_data(
                    access_token,
                    GOOGLE_FIT_STEP_DATA_TYPE,
                    start_millis,
                    end_millis,
                    GOOGLE_FIT_DAILY_BUCKET_MILLIS,
                    data_source_id=source_id,
                    bucket_period={"type": "day", "value": 1, "timeZoneId": timezone_name},
                )
            except HTTPException as exc:
                if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                    raise
                logger.warning("[GFit] Realtime steps source fetch failed | source=%s | error=%s", source_id, exc.detail)
                continue
            except (httpx.TimeoutException, httpx.TransportError):
                raise
            except Exception as exc:
                logger.warning("[GFit] Realtime steps source fetch failed | source=%s | error=%s", source_id, exc)
                continue
            GoogleFitService._log_raw_google_fit_response(
                "steps_realtime_today_source",
                source_response,
                start_millis=start_millis,
                end_millis=end_millis,
                timezone_name=timezone_name,
                data_source_id=source_id,
            )
            dataset_size = GoogleFitService._response_point_count(source_response)
            if dataset_size == 0:
                logger.info("[GFit] Skipping empty realtime steps source | source=%s | dataset_size=0", source_id)
                continue
            source_total = 0
            found_value = False
            for bucket in source_response.get("bucket", []):
                value = GoogleFitService._extract_step_count(bucket)
                if value is None or int(round(value)) <= 0:
                    continue
                found_value = True
                source_total += max(0, int(round(value)))
            if found_value and source_total > 0:
                source_totals.append({"source_id": source_id, "steps": source_total})
                break

        if source_totals:
            selected = source_totals[0]
            logger.info(
                "[GFit] Realtime today steps selected source | source=%s | steps=%s",
                selected["source_id"],
                selected["steps"],
            )
            return {"date": local_day, "steps": int(selected["steps"]), "raw": {"source_totals": source_totals}}

        logger.warning("[GFit] Realtime today steps returned no positive points | date=%s", local_day)
        return None

    @staticmethod
    async def fetch_heart_rate(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        records: list[dict[str, Any]] = []

        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            records = []
            metric_sources = GoogleFitService._prioritize_data_sources("heart_rate", data_sources)
            if not metric_sources:
                metric_sources = [
                    {
                        "dataStreamId": GOOGLE_FIT_MERGED_HEART_RATE_DATASOURCE_ID,
                        "dataType": {"name": "com.google.heart_rate.bpm"},
                    }
                ]

            for source in metric_sources:
                source_id = GoogleFitService._data_source_id(source)
                if not source_id:
                    continue
                try:
                    response_json = await GoogleFitService._fetch_source_dataset_with_raw_fallback(
                        access_token,
                        "com.google.heart_rate.bpm",
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                        data_source_id=source_id,
                        metric_name="heart_rate_source",
                        timezone_name=timezone_name,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.warning("[GFit] Heart rate source fetch failed | source=%s | error=%s", source_id, exc.detail)
                    continue
                except (httpx.TimeoutException, httpx.TransportError):
                    raise
                except Exception as exc:
                    logger.warning("[GFit] Heart rate source fetch failed | source=%s | error=%s", source_id, exc)
                    continue
                GoogleFitService._log_raw_google_fit_response(
                    "heart_rate_source",
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id=source_id,
                )
                dataset_size = GoogleFitService._response_point_count(response_json)
                if dataset_size == 0:
                    logger.info("[GFit] Skipping empty heart_rate source | source=%s | dataset_size=0", source_id)
                    continue

                source_records: list[dict[str, Any]] = []
                for bucket in response_json.get("bucket", []):
                    timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
                    value = GoogleFitService._aggregate_bucket_hour_average(bucket)
                    if timestamp is None or value is None or float(value) <= 0:
                        continue
                    source_records.append(
                        GoogleFitService._normalize_google_fit_record(
                            UserVitalTypeEnum.HEART_RATE.value,
                            timestamp,
                            round(float(value), 1),
                            timezone_name=timezone_name,
                            unit="bpm",
                        )
                    )
                logger.info(
                    "[GFit] Heart rate source count | user=%s | source=%s | records=%s | points=%s",
                    getattr(user, "id", "unknown"),
                    source_id,
                    len(source_records),
                    dataset_size,
                )
                if not source_records:
                    logger.info("[GFit] Skipping zero heart_rate source | source=%s", source_id)
                    continue
                records = sorted(source_records, key=lambda item: item["timestamp"])
                logger.info(
                    "[GFit] Selected heart_rate source | user=%s | source=%s | records=%s",
                    getattr(user, "id", "unknown"),
                    source_id,
                    len(records),
                )
                break

            if metric_sources and not records:
                logger.warning(
                    "[GFit] Heart rate source aggregates empty, retrying all_sources aggregate | user=%s | sources=%s",
                    getattr(user, "id", "unknown"),
                    [GoogleFitService._data_source_id(source) for source in metric_sources],
                )

            if not records:
                response_json = await GoogleFitService._aggregate_fit_data(
                    access_token,
                    "com.google.heart_rate.bpm",
                    start_millis,
                    end_millis,
                    60 * 60 * 1000,
                )
                GoogleFitService._log_raw_google_fit_response(
                    "heart_rate",
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id="all_sources",
                )

                if GoogleFitService._response_point_count(response_json) == 0:
                    logger.info("[GFit] Skipping empty heart_rate aggregate | dataset_size=0")
                else:
                    for bucket in response_json.get("bucket", []):
                        timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
                        value = GoogleFitService._aggregate_bucket_hour_average(bucket)
                        if timestamp is None or value is None or float(value) <= 0:
                            continue
                        records.append(
                            GoogleFitService._normalize_google_fit_record(
                                UserVitalTypeEnum.HEART_RATE.value,
                                timestamp,
                                round(float(value), 1),
                                timezone_name=timezone_name,
                                unit="bpm",
                            )
                        )
                    records = sorted(records, key=lambda item: item["timestamp"])

            logger.info(
                "[GFit] Heart rate dataset count | user=%s | window_days=%s | records=%s | sources=%s | start_ms=%s | end_ms=%s",
                getattr(user, "id", "unknown"),
                window_days,
                len(records),
                [GoogleFitService._data_source_id(source) for source in metric_sources] or ["all_sources"],
                start_millis,
                end_millis,
            )
            if records:
                break

        if not records:
            logger.warning("[GFit] Heart rate data unavailable | user=%s", getattr(user, "id", "unknown"))
            return []

        return records

    @staticmethod
    async def fetch_steps(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        records: list[dict[str, Any]] = []

        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            records = []
            metric_sources = GoogleFitService._estimated_step_sources(data_sources)
            source_id = GoogleFitService._data_source_id(metric_sources[0])
            if not source_id:
                logger.warning("[GFit] Estimated steps source unavailable | user=%s", getattr(user, "id", "unknown"))
                continue

            try:
                response_json = await GoogleFitService._aggregate_fit_data(
                    access_token,
                    GOOGLE_FIT_STEP_DATA_TYPE,
                    start_millis,
                    end_millis,
                    GOOGLE_FIT_DAILY_BUCKET_MILLIS,
                    data_source_id=source_id,
                    bucket_period={"type": "day", "value": 1, "timeZoneId": timezone_name},
                )
            except HTTPException as exc:
                if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                    raise
                logger.warning("[GFit] Estimated steps fetch failed | source=%s | error=%s", source_id, exc.detail)
                continue
            except (httpx.TimeoutException, httpx.TransportError):
                raise
            except Exception as exc:
                logger.warning("[GFit] Estimated steps fetch failed | source=%s | error=%s", source_id, exc)
                continue

            GoogleFitService._log_raw_google_fit_response(
                "steps_estimated_source",
                response_json,
                start_millis=start_millis,
                end_millis=end_millis,
                timezone_name=timezone_name,
                data_source_id=source_id,
            )
            step_summary = GoogleFitService._summarize_step_response(response_json, start_millis, end_millis)
            if step_summary["datapoints"] == 0:
                logger.warning(
                    "[GFit] data delayed: estimated steps aggregate returned empty | user=%s | source=%s | start_ms=%s | end_ms=%s",
                    getattr(user, "id", "unknown"),
                    source_id,
                    start_millis,
                    end_millis,
                )
                continue

            buckets_by_day: dict[str, dict[str, Any]] = {}
            tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
            for bucket in step_summary["buckets"]:
                bucket_start = bucket.get("start_millis")
                bucket_end = bucket.get("end_millis")
                if bucket_start is None:
                    bucket_start = start_millis
                if bucket_end is None:
                    bucket_end = min(end_millis, int(bucket_start) + GOOGLE_FIT_DAILY_BUCKET_MILLIS)

                local_day = datetime.fromtimestamp(int(bucket_start) / 1000, tz=timezone.utc).astimezone(tzinfo).date().isoformat()
                processed_steps = max(0, int(bucket.get("steps") or 0))
                day_bucket = buckets_by_day.setdefault(
                    local_day,
                    {
                        "steps": 0,
                        "datapoints": 0,
                        "raw_values": [],
                        "buckets": [],
                        "bucket_count": 0,
                        "start_millis": None,
                        "end_millis": None,
                    },
                )
                day_bucket["steps"] += processed_steps
                day_bucket["datapoints"] += int(bucket.get("datapoints") or 0)
                day_bucket["raw_values"].extend(bucket.get("raw_values", []))
                day_bucket["buckets"].append(bucket)
                day_bucket["bucket_count"] += 1
                day_bucket["start_millis"] = (
                    int(bucket_start)
                    if day_bucket["start_millis"] is None
                    else min(int(day_bucket["start_millis"]), int(bucket_start))
                )
                day_bucket["end_millis"] = (
                    int(bucket_end)
                    if day_bucket["end_millis"] is None
                    else max(int(day_bucket["end_millis"]), int(bucket_end))
                )

            for day_meta in GoogleFitService._local_day_metadata(timezone_name, start_millis, end_millis):
                local_day = day_meta["date"]
                day_start = int(day_meta["start_millis"])
                day_end = int(day_meta["end_millis"])
                effective_start = int(day_meta["effective_start_millis"])
                effective_end = int(day_meta["effective_end_millis"])
                day_bucket = buckets_by_day.get(
                    local_day,
                    {
                        "steps": 0,
                        "datapoints": 0,
                        "raw_values": [],
                        "buckets": [],
                        "bucket_count": 0,
                        "start_millis": effective_start,
                        "end_millis": effective_end,
                    },
                )
                processed_steps = max(0, int(day_bucket.get("steps") or 0))
                record = GoogleFitService._normalize_google_fit_record(
                    UserVitalTypeEnum.STEPS.value,
                    day_start,
                    processed_steps,
                    timezone_name=timezone_name,
                    unit="count",
                )
                record.update(
                    {
                        "source_used": source_id,
                        "raw_google_fit_steps": processed_steps,
                        "processed_steps": processed_steps,
                        "datapoints": int(day_bucket.get("datapoints") or 0),
                        "bucket_count": int(day_bucket.get("bucket_count") or 0),
                        "duplicate_or_overlapping_buckets": step_summary["duplicate_or_overlapping_buckets"],
                        "local_day": local_day,
                        "is_partial": bool(day_meta["is_partial"]),
                        "included_in_averages": bool(day_meta["included_in_averages"]),
                        "time_range": {
                            "start_millis": effective_start,
                            "end_millis": effective_end,
                            "day_start_millis": day_start,
                            "day_end_millis": day_end,
                            "start": datetime.fromtimestamp(effective_start / 1000, tz=timezone.utc).isoformat(),
                            "end": datetime.fromtimestamp(effective_end / 1000, tz=timezone.utc).isoformat(),
                            "day_start": datetime.fromtimestamp(day_start / 1000, tz=timezone.utc).isoformat(),
                            "day_end": datetime.fromtimestamp(day_end / 1000, tz=timezone.utc).isoformat(),
                            "timezone": timezone_name,
                        },
                        "raw_values": day_bucket.get("raw_values", []),
                        "buckets": day_bucket.get("buckets", []),
                    }
                )
                records.append(record)

            logger.info(
                "[GFit] Steps daily aggregate | user=%s | source=%s | total_steps=%s | records=%s | datapoints=%s | buckets=%s | raw_values=%s | start_ms=%s | end_ms=%s",
                getattr(user, "id", "unknown"),
                source_id,
                step_summary["total_steps"],
                len(records),
                step_summary["datapoints"],
                step_summary["bucket_count"],
                step_summary["raw_values"],
                start_millis,
                end_millis,
            )
            if records:
                break

        if not records:
            logger.warning("[GFit] Steps data unavailable | user=%s", getattr(user, "id", "unknown"))
            return []

        logger.info("[GFit] Steps records fetched: %s entries", len(records))
        return records

    @staticmethod
    def parse_sleep_minutes(sessions_response: dict[str, Any]) -> float:
        total_minutes = 0.0
        for session in sessions_response.get("session", []):
            try:
                start_millis = int(session.get("startTimeMillis"))
                end_millis = int(session.get("endTimeMillis"))
            except (TypeError, ValueError):
                continue
            if end_millis <= start_millis:
                continue
            total_minutes += (end_millis - start_millis) / 60000.0
        return round(total_minutes, 2)

    @staticmethod
    async def fetch_sleep_sessions(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
    ) -> dict[str, Any]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        payload: dict[str, Any] = {"session": [], "session_details": [], "total_minutes": 0.0}

        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            response_json = await GoogleFitService._list_sessions(
                access_token,
                start_millis=start_millis,
                end_millis=end_millis,
                activity_type=GOOGLE_FIT_SLEEP_ACTIVITY_TYPE,
            )
            session_details: list[dict[str, Any]] = []
            for session in response_json.get("session", []):
                try:
                    start_value = int(session.get("startTimeMillis"))
                    end_value = int(session.get("endTimeMillis"))
                except (TypeError, ValueError):
                    continue
                if end_value <= start_value:
                    continue

                detail = {
                    "id": session.get("id"),
                    "name": session.get("name"),
                    "start_time_millis": start_value,
                    "end_time_millis": end_value,
                    "start_time": datetime.fromtimestamp(start_value / 1000, tz=timezone.utc),
                    "end_time": datetime.fromtimestamp(end_value / 1000, tz=timezone.utc),
                    "duration_minutes": round((end_value - start_value) / 60000.0, 2),
                    "stage_minutes": {},
                }
                try:
                    detail["stage_minutes"] = await GoogleFitService._fetch_sleep_segment_details(
                        access_token,
                        start_millis=start_value,
                        end_millis=end_value,
                    )
                except (httpx.TimeoutException, httpx.TransportError):
                    raise
                except Exception as exc:
                    logger.warning("[GFit] Sleep segment parsing failed | session_id=%s | error=%s", session.get("id"), exc)
                session_details.append(detail)

            payload = {
                **response_json,
                "session_details": session_details,
                "total_minutes": GoogleFitService.parse_sleep_minutes(response_json),
                "window_days": window_days,
            }
            logger.info("[GFit] Sleep sessions fetched | window_days=%s | sessions=%s", window_days, len(session_details))
            if session_details:
                break

        return payload

    @staticmethod
    async def fetch_sleep(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE

        records: list[dict[str, Any]] = []
        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            records = []
            intervals_by_timestamp: dict[int, list[tuple[int, int]]] = defaultdict(list)
            metric_sources = [source for source in (data_sources or []) if GoogleFitService._data_source_id(source)]

            for source in metric_sources:
                source_id = GoogleFitService._data_source_id(source)
                if not source_id:
                    continue
                try:
                    response_json = await GoogleFitService._fetch_source_dataset_with_raw_fallback(
                        access_token,
                        "com.google.sleep.segment",
                        start_millis,
                        end_millis,
                        24 * 60 * 60 * 1000,
                        data_source_id=source_id,
                        metric_name="sleep_source",
                        timezone_name=timezone_name,
                        prefer_end_time=True,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.warning("[GFit] Sleep source fetch failed | source=%s | error=%s", source_id, exc.detail)
                    continue
                except (httpx.TimeoutException, httpx.TransportError):
                    raise
                except Exception as exc:
                    logger.warning("[GFit] Sleep source fetch failed | source=%s | error=%s", source_id, exc)
                    continue
                GoogleFitService._log_raw_google_fit_response(
                    "sleep_source",
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id=source_id,
                )
                dataset_size = GoogleFitService._response_point_count(response_json)
                if dataset_size == 0:
                    logger.info("[GFit] Skipping empty sleep source | source=%s | dataset_size=0", source_id)
                    continue
                source_records = 0
                for bucket in response_json.get("bucket", []):
                    timestamp = GoogleFitService._extract_bucket_end_millis(bucket) or GoogleFitService._extract_bucket_start_millis(bucket)
                    intervals = GoogleFitService._extract_sleep_intervals(bucket)
                    if timestamp is None or not intervals:
                        continue
                    intervals_by_timestamp[timestamp].extend(intervals)
                    source_records += 1
                logger.info(
                    "[GFit] Sleep source count | user=%s | source=%s | records=%s | points=%s",
                    getattr(user, "id", "unknown"),
                    source_id,
                    source_records,
                    dataset_size,
                )

            for timestamp, intervals in sorted(intervals_by_timestamp.items()):
                sleep_hours = GoogleFitService._sleep_hours_from_intervals(intervals)
                if sleep_hours <= 0:
                    continue
                sleep_start_ms = min(interval_start for interval_start, _interval_end in intervals)
                sleep_end_ms = max(interval_end for _interval_start, interval_end in intervals)
                records.append(
                    {
                        "type": UserVitalTypeEnum.SLEEP.value,
                        "value": sleep_hours,
                        "unit": "hours",
                        "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                        "source": "google_fit",
                        "timezone": timezone_name,
                        "sleep_start": datetime.fromtimestamp(sleep_start_ms / 1_000_000_000, tz=timezone.utc).isoformat(),
                        "sleep_end": datetime.fromtimestamp(sleep_end_ms / 1_000_000_000, tz=timezone.utc).isoformat(),
                        "duration_hours": round(float(sleep_hours), 2),
                    }
                )

            if metric_sources and not records:
                logger.warning(
                    "[GFit] Sleep source aggregates empty, retrying all_sources aggregate | user=%s | sources=%s",
                    getattr(user, "id", "unknown"),
                    [GoogleFitService._data_source_id(source) for source in metric_sources],
                )

            if not records:
                response_json = await GoogleFitService._aggregate_fit_data(
                    access_token,
                    "com.google.sleep.segment",
                    start_millis,
                    end_millis,
                    24 * 60 * 60 * 1000,
                )
                GoogleFitService._log_raw_google_fit_response(
                    "sleep",
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id="all_sources",
                )
                if GoogleFitService._response_point_count(response_json) == 0:
                    logger.info("[GFit] Skipping empty sleep aggregate | dataset_size=0")
                    continue

                for bucket in response_json.get("bucket", []):
                    timestamp = GoogleFitService._extract_bucket_end_millis(bucket) or GoogleFitService._extract_bucket_start_millis(bucket)
                    sleep_hours = GoogleFitService._aggregate_sleep_hours(bucket)
                    if timestamp is None or sleep_hours <= 0:
                        continue
                    records.append(
                        {
                            "type": UserVitalTypeEnum.SLEEP.value,
                            "value": sleep_hours,
                            "unit": "hours",
                            "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                            "source": "google_fit",
                            "timezone": timezone_name,
                        }
                    )

            logger.info(
                "[GFit] Sleep segment dataset count | user=%s | window_days=%s | records=%s | sources=%s | start_ms=%s | end_ms=%s",
                getattr(user, "id", "unknown"),
                window_days,
                len(records),
                [GoogleFitService._data_source_id(source) for source in metric_sources] or ["all_sources"],
                start_millis,
                end_millis,
            )
            if records:
                return records

        logger.warning("[GFit] Sleep segments empty, trying sleep sessions fallback | user=%s", getattr(user, "id", "unknown"))
        sessions_payload = await GoogleFitService.fetch_sleep_sessions(
            user,
            access_token,
            days=days,
            timezone_name=timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        for session in sessions_payload.get("session_details", []):
            duration_minutes = session.get("duration_minutes")
            timestamp = session.get("end_time")
            if duration_minutes is None or timestamp is None:
                continue
            try:
                duration_value = float(duration_minutes)
            except (TypeError, ValueError):
                continue
            if duration_value <= 0:
                continue
            records.append(
                {
                    "type": UserVitalTypeEnum.SLEEP.value,
                    "value": round(duration_value / 60.0, 2),
                    "unit": "hours",
                    "timestamp": timestamp,
                    "source": "google_fit",
                    "timezone": timezone_name,
                    "sleep_start": session.get("start_time").isoformat() if session.get("start_time") else None,
                    "sleep_end": timestamp.isoformat() if isinstance(timestamp, datetime) else None,
                    "duration_hours": round(duration_value / 60.0, 2),
                    "stage_minutes": session.get("stage_minutes") or {},
                }
            )

        if not records:
            logger.warning("[GFit] Sleep data unavailable | user=%s", getattr(user, "id", "unknown"))
            return []

        return records

    @staticmethod
    def _aggregate_scalar_value(bucket: dict[str, Any], value_index: int = 0) -> float | None:
        values: list[float] = []
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                extracted_values = GoogleFitService._extract_point_values(point)
                if len(extracted_values) > value_index:
                    values.append(float(extracted_values[value_index]))

        if not values:
            return None

        return round(sum(values) / len(values), 2)

    @staticmethod
    def _extract_bucket_blood_pressure(bucket: dict[str, Any]) -> tuple[dict[str, float | int] | None, bool]:
        latest_valid_reading: dict[str, float | int] | None = None
        invalid_duplicate_detected = False
        fallback_timestamp = (
            GoogleFitService._extract_bucket_end_millis(bucket)
            or GoogleFitService._extract_bucket_start_millis(bucket)
            or -1
        )

        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                parsed, invalid_reason = GoogleFitService._parse_blood_pressure_with_reason(point)
                if invalid_reason == "duplicate_values":
                    invalid_duplicate_detected = True
                if parsed is None:
                    continue

                point_timestamp = (
                    GoogleFitService._point_time_millis(point, prefer_end_time=True)
                    or GoogleFitService._point_time_millis(point, prefer_end_time=False)
                    or fallback_timestamp
                )
                systolic, diastolic = parsed
                candidate = {
                    "timestamp": int(point_timestamp),
                    "systolic": float(systolic),
                    "diastolic": float(diastolic),
                }
                if latest_valid_reading is None or int(candidate["timestamp"]) >= int(latest_valid_reading["timestamp"]):
                    latest_valid_reading = candidate

        if latest_valid_reading is None:
            return None, invalid_duplicate_detected

        return latest_valid_reading, invalid_duplicate_detected

    @staticmethod
    def _normalize_glucose_mmol_to_mg_dl(value: float) -> float:
        return round(float(value) * GLUCOSE_MGDL_PER_MMOLL, 1)

    @staticmethod
    def _infer_glucose_source_unit(value: float) -> str:
        return "mmol/L" if float(value) <= GLUCOSE_MMOLL_INFERENCE_MAX else "mg/dL"

    @staticmethod
    def _normalize_glucose_value(value: float) -> dict[str, float | str]:
        raw_value = round(float(value), 1)
        raw_unit = GoogleFitService._infer_glucose_source_unit(raw_value)
        if raw_unit == "mmol/L":
            normalized_value = GoogleFitService._normalize_glucose_mmol_to_mg_dl(raw_value)
        else:
            normalized_value = raw_value
        return {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "normalized_value": round(float(normalized_value), 1),
            "normalized_unit": "mg/dL",
        }

    @staticmethod
    def _normalize_body_temperature_celsius(value: float) -> float:
        # Google Fit body temperature is documented as Celsius. This guard keeps
        # manually imported Fahrenheit-like values from being stored as 98 C.
        numeric = float(value)
        if numeric > 80:
            return round((numeric - 32.0) * 5.0 / 9.0, 1)
        return round(numeric, 1)

    @staticmethod
    def _normalize_scalar_bucket_records(
        response_json: dict[str, Any],
        *,
        metric_type: str,
        unit: str,
        timezone_name: str,
        value_index: int = 0,
        value_transform: Any = None,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._aggregate_scalar_value(bucket, value_index=value_index)
            if timestamp is None or value is None:
                continue
            if value_transform is not None:
                value = value_transform(value)
            records.append(
                GoogleFitService._normalize_google_fit_record(
                    metric_type,
                    timestamp,
                    value,
                    timezone_name=timezone_name,
                    unit=unit,
                )
            )
        return records

    @staticmethod
    def _normalize_glucose_bucket_records(
        response_json: dict[str, Any],
        *,
        metric_type: str,
        unit: str,
        timezone_name: str,
        value_index: int = 0,
        value_transform: Any = None,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._aggregate_scalar_value(bucket, value_index=value_index)
            if timestamp is None or value is None:
                continue
            glucose_value = GoogleFitService._normalize_glucose_value(value)
            records.append(
                GoogleFitService._normalize_google_fit_record(
                    metric_type,
                    timestamp,
                    glucose_value["normalized_value"],
                    timezone_name=timezone_name,
                    unit=str(glucose_value["normalized_unit"]),
                    raw_value=glucose_value["raw_value"],
                    raw_unit=str(glucose_value["raw_unit"]),
                    normalized_value=glucose_value["normalized_value"],
                    normalized_unit=str(glucose_value["normalized_unit"]),
                )
            )
            logger.info(
                "GLUCOSE_PIPELINE_TRACE | stage=ingestion | timestamp=%s | raw_value=%s | raw_unit=%s | normalized_value=%s | normalized_unit=%s | stored_value=%s | stored_unit=%s",
                datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat(),
                glucose_value["raw_value"],
                glucose_value["raw_unit"],
                glucose_value["normalized_value"],
                glucose_value["normalized_unit"],
                glucose_value["normalized_value"],
                glucose_value["normalized_unit"],
            )
        return records

    @staticmethod
    async def _fetch_scalar_metric(
        user: User,
        access_token: str,
        *,
        metric_name: str,
        vital_type: UserVitalTypeEnum,
        data_type_name: str,
        summary_data_type_name: str | None,
        unit: str,
        days: int,
        timezone_name: str,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
        value_transform: Any = None,
        record_normalizer: Any = None,
    ) -> list[dict[str, Any]]:
        normalizer = record_normalizer or GoogleFitService._normalize_scalar_bucket_records
        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            metric_sources = [
                source
                for source in GoogleFitService._prioritize_data_sources(metric_name, data_sources)
                if GoogleFitService._data_source_id(source)
            ]
            records: list[dict[str, Any]] = []

            for source in metric_sources:
                source_id = GoogleFitService._data_source_id(source)
                if not source_id:
                    continue
                try:
                    response_json = await GoogleFitService._fetch_source_dataset_with_raw_fallback(
                        access_token,
                        data_type_name,
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                        data_source_id=source_id,
                        metric_name=f"{metric_name}_source",
                        timezone_name=timezone_name,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.warning("[GFit] %s source fetch failed | source=%s | error=%s", metric_name, source_id, exc.detail)
                    continue
                except (httpx.TimeoutException, httpx.TransportError):
                    raise
                except Exception as exc:
                    logger.warning("[GFit] %s source fetch failed | source=%s | error=%s", metric_name, source_id, exc)
                    continue

                GoogleFitService._log_raw_google_fit_response(
                    f"{metric_name}_source",
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id=source_id,
                )
                if metric_name == "glucose":
                    logger.info("GLUCOSE_RAW_PAYLOAD | source=%s | payload=%s", source_id, response_json)
                elif metric_name == "body_temperature":
                    logger.info("TEMP RAW: %s", response_json)
                records = normalizer(
                    response_json,
                    metric_type=vital_type.value,
                    unit=unit,
                    timezone_name=timezone_name,
                    value_transform=value_transform,
                )
                if records:
                    break

            data_types_to_try = [data_type_name]
            if summary_data_type_name and summary_data_type_name != data_type_name:
                data_types_to_try.append(summary_data_type_name)
            for candidate_data_type in data_types_to_try:
                if records:
                    break
                try:
                    response_json = await GoogleFitService._aggregate_fit_data(
                        access_token,
                        candidate_data_type,
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    if summary_data_type_name and candidate_data_type == summary_data_type_name:
                        logger.info(
                            "[GFit] Summary aggregate unavailable; treating as empty | metric=%s | data_type=%s | start_ms=%s | end_ms=%s | error=%s",
                            metric_name,
                            candidate_data_type,
                            start_millis,
                            end_millis,
                            exc.detail,
                        )
                        continue
                    raise
                GoogleFitService._log_raw_google_fit_response(
                    metric_name,
                    response_json,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id="all_sources",
                )
                if metric_name == "glucose":
                    logger.info("GLUCOSE_RAW_PAYLOAD | source=all_sources | payload=%s", response_json)
                elif metric_name == "body_temperature":
                    logger.info("TEMP RAW: %s", response_json)
                records = normalizer(
                    response_json,
                    metric_type=vital_type.value,
                    unit=unit,
                    timezone_name=timezone_name,
                    value_transform=value_transform,
                )

            logger.info(
                "[GFit] %s dataset count | user=%s | window_days=%s | records=%s | start_ms=%s | end_ms=%s",
                metric_name,
                getattr(user, "id", "unknown"),
                window_days,
                len(records),
                start_millis,
                end_millis,
            )
            if records:
                return sorted(records, key=lambda item: item["timestamp"])

        logger.warning("[GFit] %s data unavailable | user=%s", metric_name, getattr(user, "id", "unknown"))
        return []

    @staticmethod
    async def fetch_spo2(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        return await GoogleFitService._fetch_scalar_metric(
            user,
            access_token,
            metric_name="spo2",
            vital_type=UserVitalTypeEnum.SPO2,
            data_type_name=GOOGLE_FIT_SPO2_DATA_TYPE,
            summary_data_type_name=GOOGLE_FIT_SPO2_SUMMARY_DATA_TYPE,
            unit="%",
            days=days,
            timezone_name=timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            data_sources=data_sources,
        )

    @staticmethod
    async def fetch_glucose(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        return await GoogleFitService._fetch_scalar_metric(
            user,
            access_token,
            metric_name="glucose",
            vital_type=UserVitalTypeEnum.GLUCOSE,
            data_type_name=GOOGLE_FIT_GLUCOSE_DATA_TYPE,
            summary_data_type_name=GOOGLE_FIT_GLUCOSE_SUMMARY_DATA_TYPE,
            unit="mg/dL",
            days=days,
            timezone_name=timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            data_sources=data_sources,
            record_normalizer=GoogleFitService._normalize_glucose_bucket_records,
        )

    @staticmethod
    async def fetch_body_temperature(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        return await GoogleFitService._fetch_scalar_metric(
            user,
            access_token,
            metric_name="body_temperature",
            vital_type=UserVitalTypeEnum.BODY_TEMPERATURE,
            data_type_name=GOOGLE_FIT_BODY_TEMPERATURE_DATA_TYPE,
            summary_data_type_name=GOOGLE_FIT_BODY_TEMPERATURE_SUMMARY_DATA_TYPE,
            unit="celsius",
            days=days,
            timezone_name=timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            data_sources=data_sources,
            value_transform=GoogleFitService._normalize_body_temperature_celsius,
        )

    @staticmethod
    async def fetch_blood_pressure(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        records: list[dict[str, Any]] = []
        invalid_duplicate_detected = False
        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            metric_sources = [
                source
                for source in GoogleFitService._prioritize_data_sources("blood_pressure", data_sources)
                if GoogleFitService._data_source_id(source)
            ]
            response_json: dict[str, Any] | None = None

            for source in metric_sources:
                source_id = GoogleFitService._data_source_id(source)
                if not source_id:
                    continue
                try:
                    source_response = await GoogleFitService._fetch_source_dataset_with_raw_fallback(
                        access_token,
                        GOOGLE_FIT_BLOOD_PRESSURE_DATA_TYPE,
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                        data_source_id=source_id,
                        metric_name="blood_pressure_source",
                        timezone_name=timezone_name,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.warning("[GFit] blood_pressure source fetch failed | source=%s | error=%s", source_id, exc.detail)
                    continue
                except (httpx.TimeoutException, httpx.TransportError):
                    raise
                except Exception as exc:
                    logger.warning("[GFit] blood_pressure source fetch failed | source=%s | error=%s", source_id, exc)
                    continue

                GoogleFitService._log_raw_google_fit_response(
                    "blood_pressure_source",
                    source_response,
                    start_millis=start_millis,
                    end_millis=end_millis,
                    timezone_name=timezone_name,
                    data_source_id=source_id,
                )
                if source_response.get("raw_dataset_size"):
                    logger.info(
                        "BP_FALLBACK_USED | source=%s | raw_dataset_size=%s",
                        source_id,
                        source_response.get("raw_dataset_size"),
                    )
                logger.info("BP_RAW_RESPONSE | stage=google_fit_fetch | source=%s | payload=%s", source_id, source_response)
                if GoogleFitService._response_point_count(source_response) > 0:
                    response_json = source_response
                    break

            if response_json is None:
                try:
                    response_json = await GoogleFitService._aggregate_fit_data(
                        access_token,
                        GOOGLE_FIT_BLOOD_PRESSURE_DATA_TYPE,
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.warning("[GFit] blood_pressure aggregate fetch failed | error=%s", exc.detail)
                    continue
            if GoogleFitService._response_point_count(response_json) == 0:
                try:
                    response_json = await GoogleFitService._aggregate_fit_data(
                        access_token,
                        GOOGLE_FIT_BLOOD_PRESSURE_SUMMARY_DATA_TYPE,
                        start_millis,
                        end_millis,
                        60 * 60 * 1000,
                    )
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        raise
                    logger.info(
                        "[GFit] Summary aggregate unavailable; treating as empty | metric=blood_pressure | data_type=%s | start_ms=%s | end_ms=%s | error=%s",
                        GOOGLE_FIT_BLOOD_PRESSURE_SUMMARY_DATA_TYPE,
                        start_millis,
                        end_millis,
                        exc.detail,
                    )
                    continue
            GoogleFitService._log_raw_google_fit_response(
                "blood_pressure",
                response_json,
                start_millis=start_millis,
                end_millis=end_millis,
                timezone_name=timezone_name,
                data_source_id="all_sources",
            )
            logger.info("BP_RAW_RESPONSE | stage=google_fit_fetch | source=all_sources | payload=%s", response_json)
            records = []
            for bucket in response_json.get("bucket", []):
                parsed_bp, bucket_invalid_duplicate = GoogleFitService._extract_bucket_blood_pressure(bucket)
                invalid_duplicate_detected = invalid_duplicate_detected or bucket_invalid_duplicate
                if parsed_bp is None:
                    continue
                timestamp = int(parsed_bp["timestamp"])
                systolic = float(parsed_bp["systolic"])
                diastolic = float(parsed_bp["diastolic"])
                base = {
                    "unit": "mmHg",
                    "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                    "source": "google_fit",
                    "timezone": timezone_name,
                }
                records.extend(
                    [
                        {
                            **base,
                            "type": "blood_pressure",
                            "value": round(float(systolic), 1),
                            "metadata": {"systolic": systolic, "diastolic": diastolic},
                        },
                        {**base, "type": UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC.value, "value": round(float(systolic), 1)},
                        {**base, "type": UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC.value, "value": round(float(diastolic), 1)},
                    ]
                )
            logger.info(
                "[GFit] Blood pressure dataset count | user=%s | window_days=%s | records=%s",
                getattr(user, "id", "unknown"),
                window_days,
                len(records),
            )
            if records:
                return BloodPressureFetchResult(
                    sorted(records, key=lambda item: item["timestamp"]),
                    invalid_duplicate_detected=invalid_duplicate_detected,
                )
        if invalid_duplicate_detected:
            logger.warning(
                "INVALID_BP_BLOCKED | stage=google_fit_fetch | user_id=%s | source=google_fit | function_name=fetch_blood_pressure",
                getattr(user, "id", "unknown"),
            )
        logger.warning("[GFit] Blood pressure data unavailable | user=%s", getattr(user, "id", "unknown"))
        return BloodPressureFetchResult([], invalid_duplicate_detected=invalid_duplicate_detected)

    @staticmethod
    async def fetch_location(
        user: User,
        access_token: str,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        timezone_name: str | None = None,
        start_ts: Any = None,
        end_ts: Any = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        records: list[dict[str, Any]] = []
        for start_millis, end_millis, window_days in GoogleFitService._build_candidate_windows(
            timezone_name,
            start_ts=start_ts,
            end_ts=end_ts,
            days=days,
        ):
            response_json = await GoogleFitService._aggregate_fit_data(
                access_token,
                GOOGLE_FIT_LOCATION_DATA_TYPE,
                start_millis,
                end_millis,
                60 * 60 * 1000,
            )
            GoogleFitService._log_raw_google_fit_response(
                "location",
                response_json,
                start_millis=start_millis,
                end_millis=end_millis,
                timezone_name=timezone_name,
                data_source_id="all_sources",
            )
            records = []
            for bucket in response_json.get("bucket", []):
                timestamp = GoogleFitService._extract_bucket_end_millis(bucket) or GoogleFitService._extract_bucket_start_millis(bucket)
                for dataset in bucket.get("dataset", []):
                    for point in dataset.get("point", []):
                        values = GoogleFitService._extract_point_values(point)
                        if timestamp is None or len(values) < 2:
                            continue
                        latitude = float(values[0])
                        longitude = float(values[1])
                        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                            continue
                        records.append(
                            {
                                "type": "location",
                                "value": latitude,
                                "unit": "degrees",
                                "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                                "source": "google_fit",
                                "timezone": timezone_name,
                                "metadata": {
                                    "latitude": latitude,
                                    "longitude": longitude,
                                    "accuracy_meters": float(values[2]) if len(values) > 2 else None,
                                    "altitude_meters": float(values[3]) if len(values) > 3 else None,
                                },
                            }
                        )
            logger.info(
                "[GFit] Location dataset count | user=%s | window_days=%s | records=%s",
                getattr(user, "id", "unknown"),
                window_days,
                len(records),
            )
            if records:
                return sorted(records, key=lambda item: item["timestamp"])
        logger.warning("[GFit] Location data unavailable | user=%s", getattr(user, "id", "unknown"))
        return []

    @staticmethod
    def _serialize_vitals(records: list[Any]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for record in records:
            timestamp = getattr(record, "timestamp", None)
            serialized.append(
                {
                    "type": getattr(record, "vital_type", None).value if getattr(record, "vital_type", None) else None,
                    "value": getattr(record, "value", None),
                    "unit": getattr(record, "unit", None),
                    "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                    "source": getattr(record, "source", None).value if getattr(record, "source", None) else None,
                }
            )
        return serialized

    @staticmethod
    async def handle_callback(db: Session, code: str, state_token: str) -> str:
        GoogleFitService._ensure_configured()
        state_payload = GoogleFitService._parse_state_token(state_token)
        user = db.query(User).filter(User.id == uuid.UUID(state_payload["sub"]), User.is_deleted == False).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found for Google Fit callback")

        token_data = await GoogleFitService._exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google Fit access token missing")

        connection = GoogleFitService.get_connection(db, user) or GoogleFitConnection(user_id=user.id)
        device = GoogleFitService._get_or_create_device(db, user)
        device.is_active = True
        user_device = GoogleFitService._get_or_create_user_device(db, user, include_inactive=True)
        if not user_device:
            user_device = UserDevice(
                user_id=user.id,
                provider=PROVIDER_GOOGLE_FIT,
            )

        refresh_token = token_data.get("refresh_token") or decrypt_secret(connection.refresh_token_encrypted)
        expires_in = token_data.get("expires_in") or 3600
        google_email = await GoogleFitService._fetch_google_email(access_token)

        connection.device_id = device.id
        connection.default_timezone = GoogleFitService._resolve_timezone(state_payload.get("timezone"))
        connection.scopes = token_data.get("scope") or " ".join(GOOGLE_FIT_SCOPE_SET)
        connection.google_email = google_email
        connection.access_token_encrypted = encrypt_secret(access_token)
        connection.refresh_token_encrypted = encrypt_secret(refresh_token)
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        connection.last_sync_status = "connected"

        user_device.access_token = encrypt_secret(access_token)
        user_device.refresh_token = encrypt_secret(refresh_token)
        user_device.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        user_device.is_active = True

        db.add(connection)
        db.add(user_device)
        db.commit()
        try:
            emit_event("DEVICE_CONNECTED", user.id, {"provider": "google_fit"})
        except Exception:
            logger.exception("[GFit] Failed to emit device connected event for user=%s", user.id)

        onboarding_step = state_payload.get("onboarding_step")
        if onboarding_step is not None:
            try:
                step_value = max(1, min(int(onboarding_step), 6))
            except (TypeError, ValueError):
                step_value = 1
            return f"{settings.FRONTEND_APP_URL.rstrip('/')}/onboarding/step-{step_value}?{urlencode({'googleFit': 'connected'})}"

        return GoogleFitService._build_frontend_redirect(
            redirect_path=state_payload.get("redirect_path") or "/device-settings/google-fit",
            status_value="connected",
        )

    @staticmethod
    async def sync_steps(
        db: Session,
        user: User,
        timezone_name: str | None = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        silent: bool = False,
        start_ts: Any = None,
        end_ts: Any = None,
        background_sync_page: bool = False,
    ) -> dict[str, Any]:
        sync_start_time = datetime.now(timezone.utc)
        sync_start_perf = time.perf_counter()
        connection, access_token, blocked_response = await GoogleFitService.validate_sync_auth(
            db,
            user,
            timezone_name=timezone_name,
            sync_mode="background_page" if background_sync_page else "direct",
        )
        if blocked_response is not None:
            GoogleFitService._log_sync_execution_time(
                user.id,
                sync_start_time,
                sync_start_perf,
                status_value=blocked_response.get("status", "auth_blocked"),
            )
            return blocked_response

        logger.info(
            "SYNC_PAGE_START | user=%s | timezone=%s | days=%s | silent=%s | start_time=%s",
            user.id,
            timezone_name,
            days,
            silent,
            sync_start_time.isoformat(),
        )

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or connection.default_timezone)
        connection.default_timezone = resolved_timezone

        now = datetime.now(timezone.utc)
        if silent and connection.last_synced_at and (now - connection.last_synced_at).total_seconds() < 30:
            logger.info("[GFit] Silent sync requested; bypassing cached response for user=%s", user.id)

        try:
            requested_days = int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS)
        except (TypeError, ValueError):
            requested_days = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS
        sync_days = max(1, min(requested_days, GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        if start_ts is None and end_ts is None:
            fetch_start_millis, fetch_end_millis = GoogleFitService._build_recent_local_day_series_window(
                resolved_timezone,
                sync_days,
            )
            local_sync_day = datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc).astimezone(
                GoogleFitService._safe_timezone_info(resolved_timezone)
            ).date().isoformat()
        else:
            fetch_start_millis, fetch_end_millis = GoogleFitService._resolve_fetch_window(
                resolved_timezone,
                start_ts=start_ts,
                end_ts=end_ts,
                days=sync_days,
            )
            local_sync_day = datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc).astimezone(
                GoogleFitService._safe_timezone_info(resolved_timezone)
            ).date().isoformat()
        logger.info(
            "[GFit] Sync window resolved | user=%s | requested_days=%s | sync_days=%s | local_day=%s | start_ms=%s | end_ms=%s | start_ns=%s | end_ns=%s",
            user.id,
            requested_days,
            sync_days,
            local_sync_day,
            fetch_start_millis,
            fetch_end_millis,
            GoogleFitService._millis_to_nanos(fetch_start_millis),
            GoogleFitService._millis_to_nanos(fetch_end_millis),
        )
        sync_session_id = str(uuid.uuid4())
        external_failure_detected = False
        db.close()
        try:
            all_data_sources = await GoogleFitService._list_data_sources(access_token)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.warning("SYNC_BLOCKED_AUTH | user=%s | sync_mode=direct | reason=token_revoked", user.id)
                return GoogleFitService.build_sync_blocked_response(
                    db,
                    user,
                    reason="token_expired",
                    message="Google Fit authorization expired. Please reconnect Google Fit.",
                    timezone_name=resolved_timezone,
                    connected=True,
                )
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            external_failure_detected = True
            GoogleFitService._log_external_service_failure(
                operation="data_source_discovery",
                exc=exc,
                user_id=user.id,
                fallback_used=True,
            )
            all_data_sources = []
        except Exception as exc:
            logger.warning("[GFit] Data source discovery failed; using dataTypeName aggregates | user=%s | error=%s", user.id, exc)
            all_data_sources = []
        data_sources_by_metric = GoogleFitService._filter_data_sources_by_metric(all_data_sources)

        all_records: list[dict[str, Any]] = []
        step_records: list[dict[str, Any]] = []
        heart_rate_records: list[dict[str, Any]] = []
        sleep_records: list[dict[str, Any]] = []
        fetched_metric_names: list[str] = []
        overwrite_metric_names: list[str] = []
        failed_metrics: list[str] = []
        optional_metrics = GOOGLE_FIT_OPTIONAL_SYNC_METRICS
        metric_statuses: dict[str, str] = {
            metric_name: "pending"
            for metric_name in GoogleFitService.CORE_METRIC_SCOPE_REQUIREMENTS
        }
        scope_status = GoogleFitService._scope_status(connection)
        missing_scopes: list[str] = []
        logger.info(
            "[GFit] FETCHING FROM GOOGLE FIT API | user=%s | timezone=%s | days=%s",
            user.id,
            resolved_timezone,
            sync_days,
        )
        fetch_jobs = [
            ("steps", GoogleFitService.fetch_steps),
            ("heart_rate", GoogleFitService.fetch_heart_rate),
            ("sleep", GoogleFitService.fetch_sleep),
            ("spo2", GoogleFitService.fetch_spo2),
            ("glucose", GoogleFitService.fetch_glucose),
            ("blood_pressure", GoogleFitService.fetch_blood_pressure),
            ("body_temperature", GoogleFitService.fetch_body_temperature),
            ("location", GoogleFitService.fetch_location),
        ]

        for metric_name, fetcher in fetch_jobs:
            if metric_name in GoogleFitService.CORE_METRIC_SCOPE_REQUIREMENTS and not scope_status.get(metric_name, False):
                missing_scopes.append(metric_name)
                metric_statuses[metric_name] = "missing_scope"
                logger.warning("[GFit] Missing scope for metric=%s | user=%s", metric_name, user.id)
                continue

            fetch_kwargs = {
                "days": sync_days,
                "timezone_name": resolved_timezone,
                "start_ts": fetch_start_millis,
                "end_ts": fetch_end_millis,
            }
            if metric_name in data_sources_by_metric:
                fetch_kwargs["data_sources"] = data_sources_by_metric.get(metric_name, [])

            fetched = []
            last_fetch_error: Exception | None = None
            for attempt in range(1, GOOGLE_FIT_MAX_SYNC_RETRIES + 1):
                try:
                    fetched = await fetcher(
                        user,
                        access_token,
                        **fetch_kwargs,
                    )
                    last_fetch_error = None
                    break
                except HTTPException as exc:
                    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                        if metric_name in optional_metrics:
                            logger.warning(
                                "[GFit] Optional metric auth unavailable; treating as not available | user=%s | metric=%s",
                                user.id,
                                metric_name,
                            )
                            fetched = []
                            last_fetch_error = None
                            break
                        logger.warning(
                            "SYNC_BLOCKED_AUTH | user=%s | sync_mode=direct | reason=token_revoked | metric=%s",
                            user.id,
                            metric_name,
                        )
                        return GoogleFitService.build_sync_blocked_response(
                            db,
                            user,
                            reason="token_expired",
                            message="Google Fit authorization expired. Please reconnect Google Fit.",
                            timezone_name=resolved_timezone,
                            connected=True,
                        )
                    last_fetch_error = exc
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    external_failure_detected = True
                    last_fetch_error = exc
                    GoogleFitService._log_external_service_failure(
                        operation=f"fetch_{metric_name}",
                        exc=exc,
                        user_id=user.id,
                        retry_count=attempt,
                        fallback_used=True,
                    )
                except Exception as exc:
                    last_fetch_error = exc

                logger.warning(
                    "[GFit] %s fetch attempt failed | user=%s | attempt=%s/%s | error=%s",
                    metric_name,
                    user.id,
                    attempt,
                    GOOGLE_FIT_MAX_SYNC_RETRIES,
                    last_fetch_error,
                )

            if last_fetch_error is not None:
                metric_statuses[metric_name] = "not_available" if metric_name in optional_metrics else "failed"
                if metric_name not in optional_metrics:
                    failed_metrics.append(metric_name)
                logger.warning(
                    "SYNC_ABORTED | user=%s | metric=%s | reason=max_retries_exhausted | attempts=%s",
                    user.id,
                    metric_name,
                    GOOGLE_FIT_MAX_SYNC_RETRIES,
                )
                continue

            records = list(fetched or [])
            invalid_bp_blocked = (
                metric_name == "blood_pressure"
                and bool(getattr(fetched, "invalid_duplicate_detected", False))
            )
            if not (metric_name == "blood_pressure" and invalid_bp_blocked and not records):
                overwrite_metric_names.append(metric_name)
            else:
                logger.warning(
                    "INVALID_BP_BLOCKED | stage=sync_overwrite_guard | user_id=%s | source=google_fit | function_name=sync_steps",
                    user.id,
                )
            if records:
                metric_statuses[metric_name] = "ready"
                fetched_metric_names.append(metric_name)
                all_records.extend(records)
                if metric_name == "steps":
                    step_records = records
                elif metric_name == "heart_rate":
                    heart_rate_records = records
                elif metric_name == "sleep":
                    sleep_records = records
            else:
                metric_statuses[metric_name] = "not_available" if metric_name in optional_metrics else "empty"
                logger.warning("[GFit] %s fetch returned empty dataset | user=%s", metric_name, user.id)

        if all_records:
            all_records = [
                {
                    **record,
                    "sync_session_id": sync_session_id,
                }
                for record in all_records
            ]

        realtime_today_steps = None
        delayed_step_details: dict[str, dict[str, int]] = {}

        if step_records:
            existing_steps_by_day = GoogleFitService._stored_step_totals_by_day(
                db,
                user,
                timezone_name=resolved_timezone,
                start_millis=fetch_start_millis,
                end_millis=fetch_end_millis,
            )
            filtered_step_records, delayed_step_details = GoogleFitService._filter_delayed_step_records(
                step_records,
                existing_steps_by_day,
                timezone_name=resolved_timezone,
            )
            if delayed_step_details:
                logger.warning(
                    "[GFit] data delayed: keeping last known steps | user=%s | days=%s",
                    user.id,
                    delayed_step_details,
                )
                step_records = filtered_step_records
                all_records = [
                    record
                    for record in all_records
                    if record.get("type") != UserVitalTypeEnum.STEPS.value
                ]
                all_records.extend(step_records)
                if not step_records:
                    metric_statuses["steps"] = "delayed"
                    fetched_metric_names = [name for name in fetched_metric_names if name != "steps"]
                    overwrite_metric_names = [name for name in overwrite_metric_names if name != "steps"]

        if not all_records:
            empty_metrics = [
                metric_name
                for metric_name, _fetcher in fetch_jobs
                if metric_name not in fetched_metric_names
                and metric_name not in failed_metrics
                and metric_name not in missing_scopes
            ]
            logger.warning(
                "[GFit] Sync fetched zero records | user=%s | failed_metrics=%s | empty_metrics=%s | missing_scopes=%s | metric_statuses=%s | start_ms=%s | end_ms=%s",
                user.id,
                failed_metrics,
                empty_metrics,
                sorted(set(missing_scopes)),
                metric_statuses,
                fetch_start_millis,
                fetch_end_millis,
            )
            logger.warning("SYNC_ABORTED | user=%s | reason=no_records | failed_metrics=%s", user.id, failed_metrics)
            sync_timestamp = datetime.now(timezone.utc)
            data_availability = GoogleFitService._data_availability_from_user_vitals(db, user)
            vital_counts = GoogleFitService._count_user_vitals_by_metric(db, user)
            step_debug = GoogleFitService._step_debug_payload(
                db,
                user,
                [],
                {},
                timezone_name=resolved_timezone,
                start_millis=fetch_start_millis,
                end_millis=fetch_end_millis,
            )
            required_failed_metrics = [metric_name for metric_name in failed_metrics if metric_name not in optional_metrics]
            required_missing_scopes = [metric_name for metric_name in missing_scopes if metric_name not in optional_metrics]
            has_external_failure = bool(required_failed_metrics or external_failure_detected)
            delay_warning = "Google Fit sync unavailable" if has_external_failure else "Google Fit data delayed; keeping last known data."
            logger.warning("[GFit] data delayed: keeping last known data | user=%s", user.id)
            partial = bool(required_failed_metrics or required_missing_scopes)
            raw_payload = GoogleFitService._connection_raw_payload(connection)
            background_sync = raw_payload.get("background_sync")
            if isinstance(background_sync, dict):
                background_sync = {
                    **background_sync,
                    "status": "running" if background_sync_page else "completed",
                    "completed_at": sync_timestamp.isoformat(),
                    "result": "no_data",
                }
            else:
                background_sync = None

            no_data_raw_response = {
                "vitals_synced": 0,
                "data_points_fetched": 0,
                "step_records": 0,
                "realtime_today_steps": None,
                "heart_rate_records": 0,
                "sleep_records": 0,
                "spo2_records": 0,
                "glucose_records": 0,
                "blood_pressure_records": 0,
                "body_temperature_records": 0,
                "location_records": 0,
                "successful_metrics": fetched_metric_names,
                "failed_metrics": failed_metrics,
                "empty_metrics": empty_metrics,
                "missing_scopes": sorted(set(missing_scopes)),
                "metric_statuses": metric_statuses,
                "sleep": "not_available" if metric_statuses.get("sleep") != "ready" else "ready",
                "early_exit": True,
                "message": delay_warning,
                "delayed_step_details": delayed_step_details,
                "time_range": {
                    "requested_days": requested_days,
                    "sync_days": sync_days,
                    "local_day": local_sync_day,
                    "start_millis": fetch_start_millis,
                    "end_millis": fetch_end_millis,
                    "start_nanos": GoogleFitService._millis_to_nanos(fetch_start_millis),
                    "end_nanos": GoogleFitService._millis_to_nanos(fetch_end_millis),
                    "start": datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc).isoformat(),
                    "end": datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc).isoformat(),
                    "start_local": datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc).astimezone(
                        GoogleFitService._safe_timezone_info(resolved_timezone)
                    ).isoformat(),
                    "end_local": datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc).astimezone(
                        GoogleFitService._safe_timezone_info(resolved_timezone)
                    ).isoformat(),
                    "timezone": resolved_timezone,
                },
                "data_availability": data_availability,
                "dataset_counts": vital_counts,
                "debug": step_debug,
                "warning": delay_warning,
                "wearable_status": "failed" if has_external_failure else "no_data",
                "core_system": "healthy",
                "external_service_failure": {
                    "service": "google_fit",
                    "failed_metrics": required_failed_metrics,
                    "retry_count": 0,
                    "fallback_used": True,
                } if has_external_failure else None,
                "execution": {
                    "start_time": sync_start_time.isoformat(),
                    "end_time": sync_timestamp.isoformat(),
                    "duration_seconds": round(time.perf_counter() - sync_start_perf, 3),
                },
            }
            if background_sync is not None:
                no_data_raw_response["background_sync"] = background_sync

            connection.default_timezone = resolved_timezone
            connection.raw_last_response = no_data_raw_response
            connection.last_synced_at = sync_timestamp
            connection.last_sync_status = "failed" if has_external_failure else ("partial" if partial else "no_data")
            db.add(connection)
            db.commit()
            db.refresh(connection)
            status_data = GoogleFitService.get_status(db, user, resolved_timezone)
            for metric_name, count in vital_counts.items():
                logger.info("FINAL DATA STORED → count=%s metric=%s", count, metric_name)
            GoogleFitService._log_sync_execution_time(user.id, sync_start_time, sync_start_perf, status_value="no_data")
            return {
                "success": True,
                "status": "failed" if has_external_failure else "no_data",
                "wearable_status": "failed" if has_external_failure else "no_data",
                "core_system": "healthy",
                "error": None,
                "partial": partial,
                "message": delay_warning,
                "warning": delay_warning,
                "source": "google_fit",
                "connected": True,
                "missing": sorted(set(required_failed_metrics + required_missing_scopes)),
                "timezone": resolved_timezone,
                "last_synced_at": connection.last_synced_at.isoformat(),
                "stats": status_data.get("stats", GoogleFitService._build_stats([])),
                "raw_json": connection.raw_last_response,
                "google_email": connection.google_email,
                "last_sync_status": connection.last_sync_status,
                "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
                "data_availability": data_availability,
                "scope_status": scope_status,
                "missing_scopes": sorted(set(missing_scopes)),
                "metric_statuses": metric_statuses,
                "debug": step_debug,
                "needs_reconsent": bool(missing_scopes),
                "data": [],
            }

        overwrite_vital_types = [
            vital_type
            for metric_name in overwrite_metric_names
            for vital_type in GoogleFitService.METRIC_VITAL_TYPE_MAP.get(metric_name, ())
        ]
        if delayed_step_details:
            overwrite_vital_types = [
                vital_type
                for vital_type in overwrite_vital_types
                if vital_type != UserVitalTypeEnum.STEPS
            ]
        logger.info(
            "[GFit] Sync overwrite metric set | user=%s | metrics=%s | vital_types=%s",
            user.id,
            overwrite_metric_names,
            [vital_type.value for vital_type in overwrite_vital_types],
        )
        if all_records and overwrite_vital_types:
            saved_records = UserDataService.store_vitals(
                db,
                user,
                all_records,
                overwrite_window=True,
                overwrite_types=overwrite_vital_types,
                window_start=fetch_start_millis,
                window_end=fetch_end_millis,
            )
        elif all_records:
            saved_records = UserDataService.store_vitals(db, user, all_records)
        else:
            saved_records = []
        try:
            saved_wearable_metrics = UserDataService.store_wearable_metrics(db, user, all_records)
        except Exception:
            db.rollback()
            saved_wearable_metrics = []
            logger.exception("[GFit] Failed to persist wearable_metrics rows | user=%s", user.id)

        device = GoogleFitService._get_or_create_device(db, user)
        device.is_active = True
        connection.device_id = device.id
        step_rows_for_window = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.STEPS,
                UserVital.source == UserVitalSourceEnum.GOOGLE_FIT,
                UserVital.timestamp >= datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc),
                UserVital.timestamp < datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc),
            )
            .order_by(UserVital.timestamp.asc())
            .all()
        )
        daily_steps = compute_daily_steps(step_rows_for_window, resolved_timezone)
        daily_steps_by_day = {str(item["date"]): int(item["steps"]) for item in daily_steps}
        sync_timestamp = datetime.now(timezone.utc)
        data_availability = GoogleFitService._data_availability_from_user_vitals(db, user)
        vital_counts = GoogleFitService._count_user_vitals_by_metric(db, user)
        step_delay_warning = "Google Fit data delayed; keeping last known steps." if delayed_step_details else None
        empty_data_warning = step_delay_warning or ("No wearable data found in Google Fit API" if not all_records else None)
        step_debug = GoogleFitService._step_debug_payload(
            db,
            user,
            step_records,
            daily_steps_by_day,
            timezone_name=resolved_timezone,
            start_millis=fetch_start_millis,
            end_millis=fetch_end_millis,
        )
        raw_payload = GoogleFitService._connection_raw_payload(connection)
        background_sync = raw_payload.get("background_sync")
        if isinstance(background_sync, dict):
            background_sync = {
                **background_sync,
                "status": "running" if background_sync_page else "completed",
                "completed_at": sync_timestamp.isoformat(),
                "result": "partial" if failed_metrics or missing_scopes else "ready",
            }
        else:
            background_sync = None
        connection.default_timezone = resolved_timezone
        connection.raw_last_response = {
            "vitals_synced": len(saved_records),
            "wearable_metrics_synced": len(saved_wearable_metrics),
            "data_points_fetched": len(all_records),
            "step_records": len(step_records),
            "realtime_today_steps": realtime_today_steps,
            "heart_rate_records": len(heart_rate_records),
            "sleep_records": len(sleep_records),
            "spo2_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.SPO2.value]),
            "glucose_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.GLUCOSE.value]),
            "blood_pressure_records": len([record for record in all_records if str(record.get("type")) == "blood_pressure"]),
            "body_temperature_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.BODY_TEMPERATURE.value]),
            "location_records": len([record for record in all_records if str(record.get("type")) == "location"]),
            "successful_metrics": fetched_metric_names,
            "failed_metrics": failed_metrics,
            "empty_metrics": [
                metric_name
                for metric_name, _fetcher in fetch_jobs
                if metric_name not in fetched_metric_names
                and metric_name not in failed_metrics
                and metric_name not in missing_scopes
            ],
            "missing_scopes": sorted(set(missing_scopes)),
            "metric_statuses": metric_statuses,
            "delayed_step_details": delayed_step_details,
            "sleep": "not_available" if metric_statuses.get("sleep") != "ready" else "ready",
            "time_range": {
                "requested_days": requested_days,
                "sync_days": sync_days,
                "local_day": local_sync_day,
                "start_millis": fetch_start_millis,
                "end_millis": fetch_end_millis,
                "start_nanos": GoogleFitService._millis_to_nanos(fetch_start_millis),
                "end_nanos": GoogleFitService._millis_to_nanos(fetch_end_millis),
                "start": datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc).isoformat(),
                "start_local": datetime.fromtimestamp(fetch_start_millis / 1000, tz=timezone.utc).astimezone(
                    GoogleFitService._safe_timezone_info(resolved_timezone)
                ).isoformat(),
                "end_local": datetime.fromtimestamp(fetch_end_millis / 1000, tz=timezone.utc).astimezone(
                    GoogleFitService._safe_timezone_info(resolved_timezone)
                ).isoformat(),
                "timezone": resolved_timezone,
            },
            "data_types": {
                "steps": GOOGLE_FIT_STEP_DATA_TYPE,
                "heart_rate": "com.google.heart_rate.bpm",
                "sleep": "com.google.sleep.segment",
                "spo2": GOOGLE_FIT_SPO2_DATA_TYPE,
                "glucose": GOOGLE_FIT_GLUCOSE_DATA_TYPE,
                "blood_pressure": GOOGLE_FIT_BLOOD_PRESSURE_DATA_TYPE,
                "body_temperature": GOOGLE_FIT_BODY_TEMPERATURE_DATA_TYPE,
                "location": GOOGLE_FIT_LOCATION_DATA_TYPE,
            },
            "data_sources": {
                metric_name: [
                    {
                        "id": GoogleFitService._data_source_id(source),
                        "data_type": GoogleFitService._data_source_type_name(source),
                        "stream_name": source.get("dataStreamName"),
                        "source_type": source.get("type"),
                        "app": GoogleFitService._data_source_app_name(source),
                    }
                    for source in data_sources_by_metric.get(metric_name, [])
                ]
                for metric_name in GOOGLE_FIT_METRIC_DATA_TYPES
            },
            "data_availability": data_availability,
            "dataset_counts": vital_counts,
            "debug": step_debug,
            "warning": empty_data_warning,
            "wearable_status": "partial" if failed_metrics or missing_scopes or external_failure_detected else "ready",
            "core_system": "healthy",
            "external_service_failure": {
                "service": "google_fit",
                "failed_metrics": failed_metrics,
                "retry_count": 0,
                "fallback_used": True,
            } if failed_metrics or external_failure_detected else None,
            "execution": {
                "start_time": sync_start_time.isoformat(),
                "end_time": sync_timestamp.isoformat(),
                "duration_seconds": round(time.perf_counter() - sync_start_perf, 3),
            },
        }
        if background_sync is not None:
            connection.raw_last_response["background_sync"] = background_sync
        required_failed_metrics = [metric_name for metric_name in failed_metrics if metric_name not in optional_metrics]
        required_missing_scopes = [metric_name for metric_name in missing_scopes if metric_name not in optional_metrics]
        partial = bool(required_failed_metrics or required_missing_scopes)
        connection.last_synced_at = sync_timestamp
        connection.last_sync_status = "syncing" if background_sync_page else ("partial" if partial else "ready")
        db.add(connection)
        db.commit()
        db.refresh(connection)
        stored_counts = GoogleFitService._count_user_vitals_by_metric(db, user)
        for metric_name, count in stored_counts.items():
            logger.info("FINAL DATA STORED → count=%s metric=%s", count, metric_name)
        try:
            generate_health_alerts(user.id, db)
        except Exception:
            logger.exception("[GFit] Alert generation failed for user=%s", user.id)
        if saved_records:
            try:
                db.close()
                await run_in_threadpool(run_pipeline, str(user.id))
            except Exception:
                logger.exception("[GFit] Auto pipeline run failed for user=%s", user.id)
        try:
            if saved_records:
                emit_event("VITALS_UPDATED", user.id, {"source": "google_fit", "records": len(saved_records)})
            for record in saved_records:
                if record.vital_type == UserVitalTypeEnum.HEART_RATE and record.value is not None:
                    emit_event("HEART_RATE_ALERT", user.id, {"heart_rate": record.value})
                elif record.vital_type == UserVitalTypeEnum.STEPS and record.value is not None:
                    emit_event("STEPS_MILESTONE", user.id, {"steps": record.value})
                elif record.vital_type == UserVitalTypeEnum.SLEEP and record.value is not None:
                    emit_event("SLEEP_ALERT", user.id, {"sleep": record.value})
        except Exception:
            logger.exception("[GFit] Failed to emit sync notification events for user=%s", user.id)

        serialized_records = GoogleFitService._serialize_vitals(saved_records)
        stats = GoogleFitService._build_stats(daily_steps, resolved_timezone)
        message = None
        warning_message = empty_data_warning
        missing_metrics = sorted(set(required_failed_metrics + required_missing_scopes))
        if required_missing_scopes:
            message = f"Reconnect Google Fit to grant missing permissions: {', '.join(sorted(set(required_missing_scopes)))}."
        elif warning_message:
            message = warning_message
        elif partial and not step_records:
            message = "Google Fit sync completed with partial data."
        elif partial and step_records:
            message = "Steps synced. Some optional metrics were unavailable."

        GoogleFitService._log_sync_execution_time(user.id, sync_start_time, sync_start_perf, status_value=connection.last_sync_status)
        logger.info("SYNC_COMPLETE | user=%s | source=direct | status=%s | records=%s", user.id, connection.last_sync_status, len(saved_records))
        return {
            "success": True,
            "status": "ready",
            "wearable_status": "partial" if partial or external_failure_detected else "ready",
            "core_system": "healthy",
            "error": None,
            "partial": partial,
            "message": message,
            "warning": warning_message,
            "connected": True,
            "source": "google_fit",
            "missing": missing_metrics,
            "timezone": resolved_timezone,
            "last_synced_at": connection.last_synced_at.isoformat(),
            "stats": stats,
            "raw_json": connection.raw_last_response,
            "google_email": connection.google_email,
            "last_sync_status": connection.last_sync_status,
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data_availability": data_availability,
            "scope_status": scope_status,
            "missing_scopes": sorted(set(missing_scopes)),
            "debug": step_debug,
            "needs_reconsent": bool(missing_scopes),
            "data": serialized_records,
        }

    @staticmethod
    async def sync_steps_paginated(
        db: Session,
        user: User,
        timezone_name: str | None = None,
        days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
        page_size_days: int = GOOGLE_FIT_PAGE_SIZE_DAYS,
    ) -> dict[str, Any]:
        paginated_start_time = datetime.now(timezone.utc)
        paginated_start_perf = time.perf_counter()
        connection, _access_token, blocked_response = await GoogleFitService.validate_sync_auth(
            db,
            user,
            timezone_name=timezone_name,
            sync_mode="paginated",
        )
        if blocked_response is not None:
            GoogleFitService._log_sync_execution_time(
                user.id,
                paginated_start_time,
                paginated_start_perf,
                status_value=blocked_response.get("status", "auth_blocked"),
            )
            return blocked_response

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or getattr(connection, "default_timezone", None))
        requested_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
        local_day, _start_millis, _end_millis = GoogleFitService._build_current_local_day_window(resolved_timezone)
        windows = GoogleFitService._build_paginated_fetch_windows(
            resolved_timezone,
            days=requested_days,
            page_size_days=page_size_days,
        )
        logger.info("SYNC_START | user=%s | source=paginated | pages=%s | days=%s", user.id, len(windows), requested_days)
        logger.info(
            "[GFit] Paginated sync started | user=%s | requested_days=%s | page_size_days=%s | pages=%s | local_day=%s | start_time=%s",
            user.id,
            requested_days,
            page_size_days,
            len(windows),
            local_day,
            paginated_start_time.isoformat(),
        )

        page_results: list[dict[str, Any]] = []
        first_result: dict[str, Any] | None = None
        pages_with_data = 0

        for start_millis, end_millis, window_days, page_number in windows:
            # ── MID-LOOP AUTH CHECK: stop if user disconnected ──
            mid_loop_connection = GoogleFitService.get_connection(db, user)
            if not mid_loop_connection:
                logger.warning("SYNC_STOPPED_LOGOUT | user=%s | reason=connection_deleted_mid_sync | page=%s", user.id, page_number)
                break
            if (mid_loop_connection.last_sync_status or "").lower() == "disconnected":
                logger.warning("SYNC_STOPPED_LOGOUT | user=%s | reason=status_disconnected_mid_sync | page=%s", user.id, page_number)
                break
            if not mid_loop_connection.access_token_encrypted and not mid_loop_connection.refresh_token_encrypted:
                logger.warning("SYNC_AUTH_FAILED | user=%s | reason=tokens_cleared_mid_sync | page=%s", user.id, page_number)
                break

            # ── CANCELLATION CHECK ──
            if GoogleFitService._is_sync_cancelled(str(user.id)):
                logger.warning("SYNC_STOPPED_LOGOUT | user=%s | reason=cancel_flag_set_mid_sync | page=%s", user.id, page_number)
                break

            logger.info(
                "[GFit] Paginated sync page | user=%s | page=%s | window_days=%s | start_ms=%s | end_ms=%s",
                user.id,
                page_number,
                window_days,
                start_millis,
                end_millis,
            )
            db.close()
            result = await GoogleFitService.sync_steps(
                db,
                user,
                timezone_name=resolved_timezone,
                days=window_days,
                silent=False,
                start_ts=start_millis,
                end_ts=end_millis,
                background_sync_page=True,
            )
            page_results.append(result)
            if first_result is None:
                first_result = result

            raw_json = result.get("raw_json") if isinstance(result, dict) else {}
            fetched_points = int((raw_json or {}).get("data_points_fetched") or 0) if isinstance(raw_json, dict) else 0
            has_page_data = fetched_points > 0 or bool(result.get("data") if isinstance(result, dict) else [])
            if has_page_data:
                pages_with_data += 1

            if page_number == 1 and not has_page_data:
                logger.info("[GFit] Paginated sync first page empty; continuing to older daily windows | user=%s", user.id)

        if pages_with_data == 0:
            logger.warning(
                "SYNC_ABORTED | user=%s | reason=no_data | pages=%s | requested_days=%s",
                user.id,
                len(page_results),
                requested_days,
            )
            connection = GoogleFitService.get_connection(db, user)
            raw_payload = GoogleFitService._connection_raw_payload(connection)
            background_sync = raw_payload.get("background_sync")
            first_status = str((first_result or {}).get("wearable_status") or (first_result or {}).get("status") or "")
            sync_failed = first_status == "failed"
            if isinstance(background_sync, dict):
                background_sync.update(
                    {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "result": "failed" if sync_failed else "no_data",
                        "pages_requested": len(windows),
                        "pages_completed": len(page_results),
                        "pages_with_data": 0,
                    }
                )
                raw_payload["background_sync"] = background_sync
                if connection:
                    connection.raw_last_response = raw_payload
                    connection.last_sync_status = "failed" if sync_failed else "no_data"
                    db.add(connection)
                    db.commit()
                    db.refresh(connection)
                    if isinstance(first_result, dict):
                        first_result["raw_json"] = connection.raw_last_response
                        first_result["last_sync_status"] = connection.last_sync_status
            GoogleFitService._log_sync_execution_time(
                user.id,
                paginated_start_time,
                paginated_start_perf,
                status_value="failed" if sync_failed else "no_data",
            )
            return first_result or {
                "success": True,
                "status": "no_data",
                "wearable_status": "no_data",
                "core_system": "healthy",
                "message": "No data available",
                "source": "google_fit",
                "connected": True,
                "data": [],
            }

        any_page_failed = any(
            str(result.get("wearable_status") or result.get("status") or "").lower() == "failed"
            for result in page_results
        )
        final_status = "partial" if any_page_failed or not all(result.get("success", False) for result in page_results) else "ready"
        connection = GoogleFitService.get_connection(db, user)
        raw_payload = GoogleFitService._connection_raw_payload(connection)
        background_sync = raw_payload.get("background_sync")
        if isinstance(background_sync, dict):
            background_sync.update(
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "pages_requested": len(windows),
                    "pages_completed": len(page_results),
                    "pages_with_data": pages_with_data,
                }
            )
            raw_payload["background_sync"] = background_sync
        if connection:
            if isinstance(background_sync, dict):
                connection.raw_last_response = raw_payload
            connection.last_sync_status = final_status
            db.add(connection)
            db.commit()
            db.refresh(connection)

        status_data = GoogleFitService.get_status(db, user, timezone_name=resolved_timezone)
        raw_json = connection.raw_last_response if connection else None
        GoogleFitService._log_sync_execution_time(
            user.id,
            paginated_start_time,
            paginated_start_perf,
            status_value=final_status,
        )
        logger.info("SYNC_COMPLETE | user=%s | source=paginated | status=%s | pages_completed=%s", user.id, final_status, len(page_results))
        return {
            "success": True,
            "status": final_status,
            "wearable_status": "partial" if final_status != "ready" else "ready",
            "core_system": "healthy",
            "error": None,
            "partial": final_status != "ready",
            "message": "Google Fit background sync completed.",
            "source": "google_fit",
            "connected": status_data.get("connected", True),
            "sync_mode": "background",
            "requested_days": requested_days,
            "initial_window_days": min(GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS, requested_days),
            "pages_requested": len(windows),
            "pages_completed": len(page_results),
            "pages_with_data": pages_with_data,
            "timezone": status_data.get("timezone"),
            "last_synced_at": status_data.get("last_synced_at"),
            "last_sync_status": status_data.get("last_sync_status"),
            "stats": status_data.get("stats", GoogleFitService._build_stats([])),
            "raw_json": raw_json,
            "google_email": status_data.get("google_email"),
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data_availability": status_data.get("data_availability"),
            "scope_status": status_data.get("scope_status"),
            "missing_scopes": status_data.get("missing_scopes") or [],
            "needs_reconsent": status_data.get("needs_reconsent", False),
            "data": [],
        }

    @staticmethod
    async def sync_heart_rate(db: Session, user: User, timezone_name: str | None = None) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            return {
                "connected": False,
                "message": "Connect Google Fit to sync heart rate data.",
                "data": [],
            }

        if not GoogleFitService._has_any_scope(connection, (GOOGLE_FIT_BODY_SCOPE, GOOGLE_FIT_HEART_RATE_SCOPE)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit heart rate permission is missing. Please reconnect Google Fit.",
            )

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or connection.default_timezone)
        access_token = await GoogleFitService.get_valid_access_token(db, user)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )
        try:
            all_sources = await GoogleFitService._list_data_sources(access_token)
        except Exception:
            all_sources = []
        data_sources_by_metric = GoogleFitService._filter_data_sources_by_metric(all_sources)
        start_millis, end_millis = GoogleFitService._build_last_24h_window()
        normalized = await GoogleFitService.fetch_heart_rate(
            user,
            access_token,
            days=1,
            timezone_name=resolved_timezone,
            start_ts=start_millis,
            end_ts=end_millis,
            data_sources=data_sources_by_metric.get("heart_rate", []),
        )
        sync_session_id = str(uuid.uuid4())
        normalized = [
            {
                **record,
                "sync_session_id": sync_session_id,
            }
            for record in normalized
        ]
        saved_rows = UserDataService.store_vitals(
            db,
            user,
            normalized,
            overwrite_window=True,
            overwrite_types=[UserVitalTypeEnum.HEART_RATE],
            window_start=start_millis,
            window_end=end_millis,
        )

        connection.last_synced_at = datetime.now(timezone.utc)
        connection.last_sync_status = "ready"
        db.add(connection)
        db.commit()
        try:
            if saved_rows:
                emit_event("VITALS_UPDATED", user.id, {"source": "google_fit", "records": len(saved_rows)})
            for row in saved_rows:
                if row.value is not None:
                    emit_event("HEART_RATE_ALERT", user.id, {"heart_rate": row.value})
        except Exception:
            logger.exception("[GFit] Failed to emit heart rate sync notification for user=%s", user.id)

        if not saved_rows:
            return {
                "connected": True,
                "message": "No heart rate data available",
                "data": [],
            }

        return {
            "connected": True,
            "message": None,
            "data": GoogleFitService._serialize_vitals(saved_rows),
        }

    @staticmethod
    def _is_sync_cancelled(user_id: str) -> bool:
        """Check if sync was cancelled for this user (e.g. logout/disconnect)."""
        try:
            from core.celery_app import CELERY_BROKER_URL
            import redis

            cancel_key = f"gfit_sync_cancel:{user_id}"
            r = redis.Redis.from_url(CELERY_BROKER_URL.replace("/0", "/2"), decode_responses=True)
            return bool(r.exists(cancel_key))
        except Exception:
            return False

    @staticmethod
    def _set_sync_cancelled(user_id: str, ttl_seconds: int = 60) -> None:
        """Set a cancellation flag in Redis so running syncs stop immediately."""
        try:
            from core.celery_app import CELERY_BROKER_URL
            import redis

            r = redis.Redis.from_url(CELERY_BROKER_URL.replace("/0", "/2"), decode_responses=True)
            cancel_key = f"gfit_sync_cancel:{user_id}"
            r.set(cancel_key, "1", ex=ttl_seconds)
            # Also clear any active sync lock so the slot is freed
            lock_key = f"gfit_sync_lock:{user_id}"
            rate_limit_key = f"gfit_sync_rate:{user_id}"
            r.delete(lock_key, rate_limit_key)
        except Exception as exc:
            logger.warning("[GFit] Failed to set sync cancellation flag | user=%s | error=%s", user_id, exc)

    @staticmethod
    def disconnect(db: Session, user: User) -> dict[str, Any]:
        # ── SET CANCELLATION FLAG FIRST ────────────────────────
        # This ensures any running sync stops at its next checkpoint
        GoogleFitService._set_sync_cancelled(str(user.id))
        logger.info("SYNC_STOPPED_LOGOUT | user=%s | reason=disconnect_called", user.id)

        connection = GoogleFitService.get_connection(db, user)
        if connection and connection.device_id:
            device = db.query(Device).filter(Device.id == connection.device_id).first()
            if device:
                device.is_active = False

        if connection:
            connection.access_token_encrypted = None
            connection.refresh_token_encrypted = None
            connection.last_sync_status = "disconnected"
            connection.raw_last_response = None

        user_device = db.query(UserDevice).filter(
            UserDevice.user_id == user.id,
            UserDevice.provider == PROVIDER_GOOGLE_FIT,
        ).first()
        if user_device:
            user_device.access_token = None
            user_device.refresh_token = None
            user_device.token_expiry = None
            user_device.is_active = False

        if connection:
            db.delete(connection)
        db.commit()

        return {"connected": False, "message": "Google Fit disconnected"}

    @staticmethod
    def stop_sync_on_logout(db: Session, user_id: str) -> None:
        user_id_value = uuid.UUID(str(user_id))
        GoogleFitService._set_sync_cancelled(str(user_id_value))
        logger.info("SYNC_STOPPED_LOGOUT | user=%s | reason=logout", user_id_value)

        connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user_id_value).first()
        if connection:
            connection.access_token_encrypted = None
            connection.refresh_token_encrypted = None
            connection.last_sync_status = "disconnected"
            raw_payload = GoogleFitService._connection_raw_payload(connection)
            raw_payload["sync_blocked"] = {
                "reason": "logout",
                "blocked_at": datetime.now(timezone.utc).isoformat(),
            }
            connection.raw_last_response = raw_payload
            if connection.device_id:
                device = db.query(Device).filter(Device.id == connection.device_id).first()
                if device:
                    device.is_active = False

        user_device = db.query(UserDevice).filter(
            UserDevice.user_id == user_id_value,
            UserDevice.provider == PROVIDER_GOOGLE_FIT,
        ).first()
        if user_device:
            user_device.access_token = None
            user_device.refresh_token = None
            user_device.token_expiry = None
            user_device.is_active = False

        db.commit()
