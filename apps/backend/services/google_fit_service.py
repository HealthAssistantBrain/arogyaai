import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import decrypt_secret, encrypt_secret
from models import Device, DeviceTypeEnum, GoogleFitConnection, User, WearableData

GOOGLE_FIT_SCOPE = "https://www.googleapis.com/auth/fitness.activity.read"
GOOGLE_FIT_SCOPE_SET = ["openid", "email", "profile", GOOGLE_FIT_SCOPE]
GOOGLE_FIT_DATASOURCE_ID = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_FIT_AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"


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
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(status_code=400, detail=f"Unsupported timezone: {candidate}") from exc

    @staticmethod
    def _redirect_uri() -> str:
        return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/v1/google-fit/oauth/callback"

    @staticmethod
    def _build_state_token(user: User, redirect_path: str, timezone_name: str) -> str:
        safe_redirect = redirect_path if redirect_path and redirect_path.startswith("/") else "/device-settings/google-fit"
        payload = {
            "sub": str(user.id),
            "purpose": "google_fit_oauth",
            "redirect_path": safe_redirect,
            "timezone": timezone_name,
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
    async def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                    "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                    "redirect_uri": GoogleFitService._redirect_uri(),
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.is_error:
            raise HTTPException(status_code=400, detail="Google token exchange failed")
        return response.json()

    @staticmethod
    async def _refresh_access_token(connection: GoogleFitConnection) -> str:
        refresh_token = decrypt_secret(connection.refresh_token_encrypted)
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Google Fit refresh token is missing")

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
            raise HTTPException(status_code=400, detail="Google Fit token refresh failed")

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google Fit token refresh returned no access token")

        connection.access_token_encrypted = encrypt_secret(access_token)
        expires_in = token_data.get("expires_in") or 3600
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        return access_token

    @staticmethod
    async def _get_valid_access_token(db: Session, connection: GoogleFitConnection) -> str:
        if connection.token_expires_at and connection.token_expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
            cached_access_token = decrypt_secret(connection.access_token_encrypted)
            if cached_access_token:
                return cached_access_token

        access_token = await GoogleFitService._refresh_access_token(connection)
        db.flush()
        return access_token

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
        tzinfo = ZoneInfo(timezone_name)
        local_now = datetime.now(tzinfo)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=max(days - 1, 0))
        local_end = local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return int(local_start.timestamp() * 1000), int(local_end.timestamp() * 1000)

    @staticmethod
    def _extract_step_count(bucket: dict[str, Any]) -> int:
        total = 0
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for value in point.get("value", []):
                    int_val = value.get("intVal")
                    fp_val = value.get("fpVal")
                    if int_val is not None:
                        total += int(int_val)
                    elif fp_val is not None:
                        total += int(round(float(fp_val)))
        return total

    @staticmethod
    def _daily_payload_from_rows(rows: list[WearableData], timezone_name: str) -> list[dict[str, Any]]:
        tzinfo = ZoneInfo(timezone_name)
        payload = []
        for row in sorted(rows, key=lambda item: item.recorded_at or datetime.now(timezone.utc)):
            local_date = (row.recorded_at or datetime.now(timezone.utc)).astimezone(tzinfo).date().isoformat()
            payload.append({"date": local_date, "steps": int(row.step_count or 0)})
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
    def build_connect_url(user: User, timezone_name: str | None = None, redirect_path: str | None = None) -> dict[str, Any]:
        GoogleFitService._ensure_configured()
        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name)
        state = GoogleFitService._build_state_token(
            user=user,
            redirect_path=redirect_path or "/device-settings/google-fit",
            timezone_name=resolved_timezone,
        )
        query = urlencode(
            {
                "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                "redirect_uri": GoogleFitService._redirect_uri(),
                "response_type": "code",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "scope": " ".join(GOOGLE_FIT_SCOPE_SET),
                "state": state,
            }
        )
        return {
            "auth_url": f"{GOOGLE_AUTH_URL}?{query}",
            "redirect_uri": GoogleFitService._redirect_uri(),
            "timezone": resolved_timezone,
        }

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

        refresh_token = token_data.get("refresh_token") or decrypt_secret(connection.refresh_token_encrypted)
        google_email = await GoogleFitService._fetch_google_email(access_token)
        expires_in = token_data.get("expires_in") or 3600

        connection.device_id = device.id
        connection.google_email = google_email
        connection.default_timezone = GoogleFitService._resolve_timezone(state_payload.get("timezone"))
        connection.scopes = token_data.get("scope") or " ".join(GOOGLE_FIT_SCOPE_SET)
        connection.access_token_encrypted = encrypt_secret(access_token)
        connection.refresh_token_encrypted = encrypt_secret(refresh_token)
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        connection.last_sync_status = "connected"

        db.add(connection)
        db.commit()

        return GoogleFitService._build_frontend_redirect(
            redirect_path=state_payload.get("redirect_path") or "/device-settings/google-fit",
            status_value="connected",
        )

    @staticmethod
    async def sync_steps(db: Session, user: User, timezone_name: str | None = None, days: int = 30) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            raise HTTPException(status_code=404, detail="Google Fit is not connected")

        resolved_timezone = GoogleFitService._resolve_timezone(timezone_name or connection.default_timezone)
        connection.default_timezone = resolved_timezone
        access_token = await GoogleFitService._get_valid_access_token(db, connection)
        start_millis, end_millis = GoogleFitService._build_bucket_window(resolved_timezone, days=max(1, min(days, 90)))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GOOGLE_FIT_AGGREGATE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "aggregateBy": [{"dataSourceId": GOOGLE_FIT_DATASOURCE_ID}],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": start_millis,
                    "endTimeMillis": end_millis,
                },
            )

        if response.is_error:
            connection.last_sync_status = "error"
            db.commit()
            raise HTTPException(status_code=400, detail="Failed to fetch Google Fit steps")

        payload = response.json()
        device = GoogleFitService._get_or_create_device(db, user)
        device.is_active = True

        tzinfo = ZoneInfo(resolved_timezone)
        daily_steps: list[dict[str, Any]] = []

        for bucket in payload.get("bucket", []):
            start_value = bucket.get("startTimeMillis")
            if start_value is None and bucket.get("startTimeNanos"):
                start_value = int(bucket["startTimeNanos"]) // 1_000_000
            if start_value is None:
                continue

            bucket_datetime = datetime.fromtimestamp(int(start_value) / 1000, tz=timezone.utc).astimezone(tzinfo)
            bucket_day = bucket_datetime.date().isoformat()
            daily_steps.append({"date": bucket_day, "steps": GoogleFitService._extract_step_count(bucket)})

        start_dt_utc = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc)
        end_dt_utc = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc)
        db.query(WearableData).filter(
            WearableData.user_id == user.id,
            WearableData.device_id == device.id,
            WearableData.recorded_at >= start_dt_utc,
            WearableData.recorded_at < end_dt_utc,
        ).delete(synchronize_session=False)

        for item in daily_steps:
            local_day = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=tzinfo)
            db.add(
                WearableData(
                    user_id=user.id,
                    device_id=device.id,
                    recorded_at=local_day.astimezone(timezone.utc),
                    step_count=item["steps"],
                )
            )

        connection.device_id = device.id
        connection.raw_last_response = payload
        connection.last_synced_at = datetime.now(timezone.utc)
        connection.last_sync_status = "ready"
        db.add(connection)
        db.commit()
        db.refresh(connection)

        stats = GoogleFitService._build_stats(sorted(daily_steps, key=lambda item: item["date"]))
        return {
            "connected": True,
            "timezone": resolved_timezone,
            "last_synced_at": connection.last_synced_at.isoformat(),
            "stats": stats,
            "raw_json": payload,
            "google_email": connection.google_email,
            "last_sync_status": connection.last_sync_status,
            "data_source_id": GOOGLE_FIT_DATASOURCE_ID,
        }

    @staticmethod
    def disconnect(db: Session, user: User) -> dict[str, Any]:
        connection = GoogleFitService.get_connection(db, user)
        if not connection:
            return {"connected": False, "message": "Google Fit already disconnected"}

        if connection.device_id:
            device = db.query(Device).filter(Device.id == connection.device_id).first()
            if device:
                device.is_active = False

        connection.access_token_encrypted = None
        connection.refresh_token_encrypted = None
        connection.last_sync_status = "disconnected"
        connection.raw_last_response = None
        db.delete(connection)
        db.commit()

        return {"connected": False, "message": "Google Fit disconnected"}
