import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import decrypt_secret, encrypt_secret
from models import (
    Device,
    DeviceTypeEnum,
    GoogleFitConnection,
    PROVIDER_GOOGLE_FIT,
    User,
    VitalsData,
    WearableData,
    UserDevice,
    UserVitalTypeEnum,
)
from services.user_data_service import UserDataService
from services.event_service import emit_event

GOOGLE_FIT_ACTIVITY_SCOPE = "https://www.googleapis.com/auth/fitness.activity.read"
GOOGLE_FIT_HEART_RATE_SCOPE = "https://www.googleapis.com/auth/fitness.heart_rate.read"
GOOGLE_FIT_SLEEP_SCOPE = "https://www.googleapis.com/auth/fitness.sleep.read"
GOOGLE_FIT_OXYGEN_SCOPE = "https://www.googleapis.com/auth/fitness.oxygen_saturation.read"
GOOGLE_FIT_SCOPE_SET = [
    "openid",
    "email",
    "profile",
    GOOGLE_FIT_ACTIVITY_SCOPE,
    GOOGLE_FIT_HEART_RATE_SCOPE,
    GOOGLE_FIT_SLEEP_SCOPE,
    GOOGLE_FIT_OXYGEN_SCOPE,
]
GOOGLE_FIT_DATASOURCE_ID = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_FIT_AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
GOOGLE_FIT_DATA_SOURCE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataSources"
logger = logging.getLogger("google_fit_service")


class GoogleFitService:
    @staticmethod
    def _ensure_configured() -> None:
        if not settings.GOOGLE_FIT_CLIENT_ID or not settings.GOOGLE_FIT_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Fit is not configured on the server",
            )

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
    async def _get_valid_user_device_access_token(db: Session, user_device: UserDevice) -> str:
        if user_device.token_expiry and user_device.token_expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
            cached_access_token = decrypt_secret(user_device.access_token)
            if cached_access_token:
                return cached_access_token

        refresh_token = decrypt_secret(user_device.refresh_token)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
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

        user_device.access_token = encrypt_secret(access_token)
        expires_in = token_data.get("expires_in") or 3600
        user_device.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
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

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
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
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.is_error:
            return None
        return response.json().get("email")

    @staticmethod
    def _build_bucket_window(timezone_name: str, days: int) -> tuple[int, int]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        local_now = datetime.now(tzinfo)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=max(days - 1, 0))
        local_end = local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return int(local_start.timestamp() * 1000), int(local_end.timestamp() * 1000)

    @staticmethod
    def _build_local_day_series(timezone_name: str, start_millis: int, end_millis: int) -> list[str]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        start_local = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc).astimezone(tzinfo).date()
        end_local = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc).astimezone(tzinfo).date()

        series: list[str] = []
        cursor = start_local
        while cursor < end_local:
            series.append(cursor.isoformat())
            cursor += timedelta(days=1)
        return series

    @staticmethod
    def _extract_step_count(bucket: dict[str, Any]) -> int | None:
        total = 0.0
        found_value = False
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                if not point:
                    continue
                point_values = GoogleFitService._extract_point_values(point)
                if not point_values:
                    continue

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
    def _aggregate_sleep_hours(bucket: dict[str, Any]) -> float:
        sleep_stage_values = {0, 2, 4, 5, 6}
        total_seconds = 0.0

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

                total_seconds += max(0.0, (int(end_nanos) - int(start_nanos)) / 1_000_000_000)

        return round(total_seconds / 3600.0, 2)

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
    def _log_raw_google_fit_response(metric_name: str, response_json: dict[str, Any]) -> None:
        print("RAW GOOGLE FIT RESPONSE:", response_json)
        print("RAW BUCKET:", response_json.get("bucket"))
        logger.info(
            "[GFit] Raw response received | metric=%s | buckets=%s",
            metric_name,
            len(response_json.get("bucket", [])) if isinstance(response_json, dict) else "unknown",
        )

    @staticmethod
    async def _aggregate_fit_data(
        access_token: str,
        data_type_name: str,
        start_millis: int,
        end_millis: int,
        bucket_duration_millis: int,
        data_source_id: str | None = None,
    ) -> dict[str, Any]:
        aggregate_by: list[dict[str, str]] = []
        if data_source_id:
            aggregate_by.append({"dataSourceId": data_source_id})
        else:
            aggregate_by.append({"dataTypeName": data_type_name})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GOOGLE_FIT_AGGREGATE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "aggregateBy": aggregate_by,
                    "bucketByTime": {"durationMillis": bucket_duration_millis},
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
            raise HTTPException(status_code=400, detail=f"Failed to fetch Google Fit data for {data_type_name}")

        return response.json()

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
                {
                    "timestamp": timestamp,
                    "heart_rate": heart_rate,
                }
            )

        return sorted(normalized, key=lambda item: item["timestamp"])

    @staticmethod
    async def _fetch_heart_rate_payload(access_token: str, timezone_name: str | None = None) -> dict[str, Any]:
        timezone_name = timezone_name or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
        _, start_millis, end_millis = GoogleFitService._build_bucket_window(timezone_name, 1)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GOOGLE_FIT_AGGREGATE_URL,
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
    def save_heart_rate(db: Session, user_id: uuid.UUID, data_list: list[dict[str, Any]]) -> list[VitalsData]:
        if not data_list:
            return []

        timestamps: list[datetime] = []
        for item in data_list:
            recorded_at = GoogleFitService._coerce_utc_datetime(item.get("timestamp"))
            if recorded_at is None:
                continue
            timestamps.append(recorded_at)

        if not timestamps:
            return []

        min_recorded_at = min(timestamps)
        max_recorded_at = max(timestamps)
        query_start = min_recorded_at.replace(minute=0, second=0, microsecond=0)

        existing_rows = (
            db.query(VitalsData)
            .filter(
                VitalsData.user_id == user_id,
                VitalsData.recorded_at >= query_start,
                VitalsData.recorded_at <= max_recorded_at,
            )
            .all()
        )

        rows_by_timestamp: dict[int, VitalsData] = {}
        for row in existing_rows:
            if row.recorded_at is None:
                continue
            row_timestamp = row.recorded_at.astimezone(timezone.utc)
            exact_key = int(row_timestamp.timestamp() * 1000)
            legacy_key = int(row_timestamp.replace(minute=0, second=0, microsecond=0).timestamp() * 1000)
            rows_by_timestamp[exact_key] = row
            rows_by_timestamp[legacy_key] = row

        saved_rows: list[VitalsData] = []
        for item in data_list:
            recorded_at = GoogleFitService._coerce_utc_datetime(item.get("timestamp"))
            if recorded_at is None:
                continue
            timestamp_key = int(recorded_at.timestamp() * 1000)
            legacy_key = int(recorded_at.replace(minute=0, second=0, microsecond=0).timestamp() * 1000)
            try:
                heart_rate_bpm = int(round(float(item["heart_rate"])))
            except (TypeError, ValueError):
                continue

            row = rows_by_timestamp.get(timestamp_key) or rows_by_timestamp.get(legacy_key)
            if row:
                if row.recorded_at is None or row.recorded_at != recorded_at:
                    row.recorded_at = recorded_at
                row.heart_rate_bpm = heart_rate_bpm
            else:
                row = VitalsData(
                    user_id=user_id,
                    recorded_at=recorded_at,
                    heart_rate_bpm=heart_rate_bpm,
                )
                db.add(row)
            rows_by_timestamp[timestamp_key] = row
            rows_by_timestamp[legacy_key] = row

            saved_rows.append(row)

        db.commit()
        return sorted(saved_rows, key=lambda item: item.recorded_at or datetime.now(timezone.utc))

    @staticmethod
    def _serialize_heart_rate(rows: list[VitalsData], timezone_name: str) -> list[dict[str, Any]]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        payload: list[dict[str, Any]] = []

        for row in rows:
            if row.recorded_at is None or row.heart_rate_bpm is None:
                continue

            local_timestamp = row.recorded_at.astimezone(tzinfo)
            payload.append(
                {
                    "timestamp": row.recorded_at.isoformat(),
                    "time": local_timestamp.strftime("%I %p").lstrip("0"),
                    "bpm": int(row.heart_rate_bpm),
                }
            )

        return payload

    @staticmethod
    def _daily_payload_from_rows(rows: list[WearableData], timezone_name: str) -> list[dict[str, Any]]:
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        payload = []
        for row in sorted(rows, key=lambda item: item.recorded_at or datetime.now(timezone.utc)):
            if row.recorded_at is None or row.step_count is None:
                continue

            local_date = row.recorded_at.astimezone(tzinfo).date().isoformat()
            payload.append({"date": local_date, "steps": int(row.step_count)})
        return payload

    @staticmethod
    def _build_stats(daily_steps: list[dict[str, Any]]) -> dict[str, Any]:
        if not daily_steps:
            return {
                "daily_steps": [],
                "total_steps": 0,
                "average_daily_steps": 0,
                "average_steps_on_active_days": 0,
                "best_day": None,
                "latest_day": None,
                "active_day_count": 0,
            }

        total_steps = sum(item["steps"] for item in daily_steps)
        active_days = [item for item in daily_steps if item["steps"] > 0]
        best_day = max(daily_steps, key=lambda item: item["steps"])
        latest_day = daily_steps[-1]

        return {
            "daily_steps": daily_steps,
            "total_steps": total_steps,
            "average_daily_steps": round(total_steps / len(daily_steps)),
            "average_steps_on_active_days": round(sum(item["steps"] for item in active_days) / len(active_days)) if active_days else 0,
            "best_day": best_day,
            "latest_day": latest_day,
            "active_day_count": len(active_days),
        }

    @staticmethod
    def _build_frontend_redirect(redirect_path: str, status_value: str, message: str | None = None) -> str:
        target = f"{settings.FRONTEND_APP_URL.rstrip('/')}{redirect_path}"
        params = {"googleFit": status_value}
        if message:
            params["message"] = message
        return f"{target}?{urlencode(params)}"

    @staticmethod
    def _has_scope(connection: GoogleFitConnection, scope: str) -> bool:
        granted_scopes = (connection.scopes or "").split()
        return scope in granted_scopes

    @staticmethod
    def get_connection(db: Session, user: User) -> GoogleFitConnection | None:
        return db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user.id).first()

    @staticmethod
    def get_status(db: Session, user: User, timezone_name: str | None = None) -> dict[str, Any]:
        timezone_name = GoogleFitService._resolve_timezone(timezone_name)
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            return {
                "connected": False,
                "timezone": timezone_name,
                "last_synced_at": None,
                "stats": GoogleFitService._build_stats([]),
                "raw_json": None,
                "google_email": None,
            }

        effective_timezone = GoogleFitService._resolve_timezone(connection.default_timezone or timezone_name)
        device = db.query(Device).filter(Device.id == connection.device_id).first() if connection.device_id else None
        rows = []
        if device:
            start_millis, _ = GoogleFitService._build_bucket_window(effective_timezone, 30)
            start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
            rows = (
                db.query(WearableData)
                .filter(
                    WearableData.user_id == user.id,
                    WearableData.device_id == device.id,
                    WearableData.recorded_at >= start_dt_utc,
                )
                .order_by(WearableData.recorded_at.asc())
                .all()
            )

        daily_steps = GoogleFitService._daily_payload_from_rows(rows, effective_timezone)
        return {
            "connected": True,
            "timezone": effective_timezone,
            "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
            "stats": GoogleFitService._build_stats(daily_steps),
            "raw_json": connection.raw_last_response,
            "google_email": connection.google_email,
            "last_sync_status": connection.last_sync_status,
        }

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
        tzinfo = GoogleFitService._safe_timezone_info(timezone_name)
        now_local = datetime.now(tzinfo)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_local.date().isoformat(), int(start_local.timestamp() * 1000), int(now_local.timestamp() * 1000)

    @staticmethod
    async def _fetch_realtime_today_steps(access_token: str, timezone_name: str) -> dict[str, Any] | None:
        local_day, start_millis, end_millis = GoogleFitService._build_current_local_day_window(timezone_name)
        dataset_id = f"{start_millis * 1_000_000}-{end_millis * 1_000_000}"
        encoded_source = quote(GOOGLE_FIT_DATASOURCE_ID, safe="")
        url = f"{GOOGLE_FIT_DATA_SOURCE_URL}/{encoded_source}/datasets/{dataset_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Fit authorization expired. Please reconnect Google Fit.",
            )

        if response.is_error:
            logger.warning("[GFit] Realtime steps fetch failed | status=%s | body=%s", response.status_code, response.text)
            return None

        payload = response.json()
        total_steps = 0.0
        for point in payload.get("point", []):
            for value in point.get("value", []):
                extracted = GoogleFitService._extract_numeric_value(value)
                if extracted is None:
                    continue
                total_steps += extracted

        return {"date": local_day, "steps": max(0, int(round(total_steps))), "raw": payload}

    @staticmethod
    async def fetch_heart_rate(
        user: User,
        access_token: str,
        days: int = 1,
        timezone_name: str | None = None,
    ) -> list[dict[str, Any]] | None:
        timezone_name, start_millis, end_millis = GoogleFitService._fetch_window_for_user(user, days, timezone_name)
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            "com.google.heart_rate.bpm",
            start_millis,
            end_millis,
            60 * 60 * 1000,
        )
        GoogleFitService._log_raw_google_fit_response("heart_rate", response_json)

        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._aggregate_bucket_hour_average(bucket)
            if timestamp is None or value is None:
                continue
            records.append(
                {
                    "type": UserVitalTypeEnum.HEART_RATE.value,
                    "value": value,
                    "unit": "bpm",
                    "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                    "source": "google_fit",
                    "timezone": timezone_name,
                }
            )
        if not records:
            logger.warning("[GFit] HEART RATE DATA NOT AVAILABLE FROM GOOGLE FIT")
            return None

        return records

    @staticmethod
    async def fetch_steps(
        user: User,
        access_token: str,
        days: int = 1,
        timezone_name: str | None = None,
    ) -> list[dict[str, Any]] | None:
        timezone_name, start_millis, end_millis = GoogleFitService._fetch_local_bucket_window_for_user(user, days, timezone_name)
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            "com.google.step_count.delta",
            start_millis,
            end_millis,
            24 * 60 * 60 * 1000,
            data_source_id=GOOGLE_FIT_DATASOURCE_ID,
        )
        GoogleFitService._log_raw_google_fit_response("steps", response_json)

        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._extract_step_count(bucket)
            if timestamp is None or value is None:
                continue
            records.append(
                {
                    "type": UserVitalTypeEnum.STEPS.value,
                    "value": value,
                    "unit": "count",
                    "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                    "source": "google_fit",
                    "timezone": timezone_name,
                }
            )
        if not records:
            logger.warning("[GFit] STEPS DATA NOT AVAILABLE FROM GOOGLE FIT")
            return None

        return records

    @staticmethod
    async def fetch_sleep(
        user: User,
        access_token: str,
        days: int = 1,
        timezone_name: str | None = None,
    ) -> list[dict[str, Any]] | None:
        timezone_name, start_millis, end_millis = GoogleFitService._fetch_window_for_user(user, days, timezone_name)
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            "com.google.sleep.segment",
            start_millis,
            end_millis,
            24 * 60 * 60 * 1000,
        )
        GoogleFitService._log_raw_google_fit_response("sleep", response_json)

        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._aggregate_sleep_hours(bucket)
            if timestamp is None or value <= 0:
                continue
            records.append(
                {
                    "type": UserVitalTypeEnum.SLEEP.value,
                    "value": value,
                    "unit": "hours",
                    "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                    "source": "google_fit",
                    "timezone": timezone_name,
                }
            )
        if not records:
            logger.warning("[GFit] SLEEP DATA NOT AVAILABLE FROM GOOGLE FIT")
            return None

        return records

    @staticmethod
    async def fetch_spo2(
        user: User,
        access_token: str,
        days: int = 1,
        timezone_name: str | None = None,
    ) -> list[dict[str, Any]] | None:
        timezone_name, start_millis, end_millis = GoogleFitService._fetch_window_for_user(user, days, timezone_name)
        response_json = await GoogleFitService._aggregate_fit_data(
            access_token,
            "com.google.oxygen_saturation.summary",
            start_millis,
            end_millis,
            24 * 60 * 60 * 1000,
        )
        GoogleFitService._log_raw_google_fit_response("spo2", response_json)

        records: list[dict[str, Any]] = []
        for bucket in response_json.get("bucket", []):
            timestamp = GoogleFitService._extract_bucket_start_millis(bucket)
            value = GoogleFitService._aggregate_oxygen_average(bucket)
            if timestamp is None or value is None:
                continue
            records.append(
                {
                    "type": UserVitalTypeEnum.SPO2.value,
                    "value": value,
                    "unit": "%",
                    "timestamp": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
                    "source": "google_fit",
                    "timezone": timezone_name,
                }
            )
        if not records:
            logger.warning("[GFit] SPO2 DATA NOT AVAILABLE FROM GOOGLE FIT")
            return None

        return records

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

        connection.device_id = device.id
        connection.default_timezone = GoogleFitService._resolve_timezone(state_payload.get("timezone"))
        connection.scopes = token_data.get("scope") or " ".join(GOOGLE_FIT_SCOPE_SET)
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
    async def sync_steps(db: Session, user: User, timezone_name: str | None = None, days: int = 30) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            logger.warning("[GFit] Sync requested for user=%s but Google Fit is not connected", user.id)
            return {
                "success": True,
                "status": "ready",
                "error": None,
                "partial": True,
                "message": "Google Fit is not connected",
                "connected": False,
                "data": [],
                "stats": GoogleFitService._build_stats([]),
                "raw_json": None,
                "google_email": None,
                "last_synced_at": None,
                "last_sync_status": "disconnected",
                "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            }

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or connection.default_timezone)
        connection.default_timezone = resolved_timezone
        access_token = await GoogleFitService.get_valid_access_token(db, user)
        if not access_token:
            logger.warning("[GFit] Sync requested for user=%s but Google Fit access token is unavailable", user.id)
            return {
                "success": True,
                "status": "ready",
                "error": None,
                "partial": True,
                "message": "Google Fit authorization expired. Please reconnect Google Fit.",
                "connected": True,
                "data": [],
                "stats": GoogleFitService._build_stats([]),
                "raw_json": None,
                "google_email": connection.google_email,
                "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
                "last_sync_status": connection.last_sync_status,
                "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            }

        sync_days = max(1, min(days, 90))
        all_records: list[dict[str, Any]] = []
        step_records: list[dict[str, Any]] = []
        fetched_metric_names: list[str] = []
        failed_metrics: list[str] = []
        fetch_jobs = [
            ("steps", GoogleFitService.fetch_steps),
            ("heart_rate", GoogleFitService.fetch_heart_rate),
            ("sleep", GoogleFitService.fetch_sleep),
            ("spo2", GoogleFitService.fetch_spo2),
        ]

        for metric_name, fetcher in fetch_jobs:
            try:
                fetched = await fetcher(user, access_token, days=sync_days, timezone_name=resolved_timezone)
            except Exception as exc:
                failed_metrics.append(metric_name)
                logger.warning(
                    "[GFit] %s fetch failed for user=%s: %s",
                    metric_name,
                    user.id,
                    exc,
                )
                continue

            records = fetched or []
            if records:
                fetched_metric_names.append(metric_name)
                all_records.extend(records)
                if metric_name == "steps":
                    step_records = records
            else:
                logger.info("[GFit] %s fetch returned no records for user=%s", metric_name, user.id)

        saved_records = UserDataService.store_vitals(db, user, all_records) if all_records else []

        device = GoogleFitService._get_or_create_device(db, user)
        device.is_active = True

        tzinfo = GoogleFitService._safe_timezone_info(resolved_timezone)
        start_millis, end_millis = GoogleFitService._build_bucket_window(resolved_timezone, days=sync_days)
        daily_steps_map = {
            day: {"date": day, "steps": 0}
            for day in GoogleFitService._build_local_day_series(resolved_timezone, start_millis, end_millis)
        }

        if step_records:
            for record in step_records:
                timestamp = record.get("timestamp")
                if not isinstance(timestamp, datetime):
                    continue
                raw_value = record.get("value")
                if raw_value is None:
                    continue
                try:
                    steps_value = int(round(float(raw_value)))
                except (TypeError, ValueError):
                    continue
                steps_value = max(0, steps_value)
                day = timestamp.astimezone(tzinfo).date().isoformat()
                daily_steps_map[day] = {"date": day, "steps": steps_value}

        realtime_today_steps = None
        try:
            realtime_today_steps = await GoogleFitService._fetch_realtime_today_steps(access_token, resolved_timezone)
        except Exception as exc:
            logger.warning("[GFit] Realtime today steps fetch failed for user=%s: %s", user.id, exc)

        if realtime_today_steps:
            daily_steps_map[realtime_today_steps["date"]] = {
                "date": realtime_today_steps["date"],
                "steps": int(realtime_today_steps["steps"]),
            }

        start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
        end_dt_utc = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc)
        db.query(WearableData).filter(
            WearableData.user_id == user.id,
            WearableData.device_id == device.id,
            WearableData.recorded_at >= start_dt_utc,
            WearableData.recorded_at < end_dt_utc,
        ).delete(synchronize_session=False)

        for item in [daily_steps_map[day] for day in sorted(daily_steps_map)]:
            local_day = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=tzinfo)
            db.add(
                WearableData(
                    user_id=user.id,
                    device_id=device.id,
                    recorded_at=local_day.astimezone(timezone.utc),
                    step_count=item["steps"],
                )
            )

        daily_steps = [daily_steps_map[day] for day in sorted(daily_steps_map)]

        connection.device_id = device.id
        sync_timestamp = datetime.now(timezone.utc)
        connection.raw_last_response = {
            "vitals_synced": len(saved_records),
            "step_records": len(step_records),
            "realtime_today_steps": realtime_today_steps,
            "heart_rate_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.HEART_RATE.value]),
            "sleep_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.SLEEP.value]),
            "spo2_records": len([record for record in all_records if record.get("type") == UserVitalTypeEnum.SPO2.value]),
            "successful_metrics": fetched_metric_names,
            "failed_metrics": failed_metrics,
        }
        connection.last_synced_at = sync_timestamp
        connection.last_sync_status = "partial" if failed_metrics else "ready"
        db.add(connection)
        db.commit()
        db.refresh(connection)
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
        stats = GoogleFitService._build_stats(sorted(daily_steps, key=lambda item: item["date"]))
        message = None
        partial = bool(failed_metrics)
        missing_metrics = sorted(set(failed_metrics))
        if not serialized_records:
            message = "No data available"
        elif partial and not step_records:
            message = "Google Fit sync completed with partial data."
        elif partial and step_records:
            message = "Steps synced. Some optional metrics were unavailable."

        return {
            "success": True,
            "status": "ready",
            "error": None,
            "partial": partial,
            "message": message,
            "connected": True,
            "missing": missing_metrics,
            "timezone": resolved_timezone,
            "last_synced_at": connection.last_synced_at.isoformat(),
            "stats": stats,
            "raw_json": connection.raw_last_response,
            "google_email": connection.google_email,
            "last_sync_status": connection.last_sync_status,
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
            "data": serialized_records,
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

        if not GoogleFitService._has_scope(connection, GOOGLE_FIT_HEART_RATE_SCOPE):
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
        payload = await GoogleFitService._fetch_heart_rate_payload(access_token, resolved_timezone)
        normalized = GoogleFitService.normalize_heart_rate_payload(payload)
        saved_rows = GoogleFitService.save_heart_rate(db, user.id, normalized)

        connection.last_synced_at = datetime.now(timezone.utc)
        connection.last_sync_status = "ready"
        db.add(connection)
        db.commit()
        try:
            if saved_rows:
                emit_event("VITALS_UPDATED", user.id, {"source": "google_fit", "records": len(saved_rows)})
            for row in saved_rows:
                if row.heart_rate_bpm is not None:
                    emit_event("HEART_RATE_ALERT", user.id, {"heart_rate": row.heart_rate_bpm})
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
            "data": GoogleFitService._serialize_heart_rate(saved_rows, resolved_timezone),
        }

    @staticmethod
    def disconnect(db: Session, user: User) -> dict[str, Any]:
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
