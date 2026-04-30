from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import HTTPException, status

from models import NotificationDevice, User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_push_device(device: NotificationDevice) -> dict[str, Any]:
    return {
        "id": str(device.id),
        "kind": "push_subscription",
        "provider": "browser-push",
        "name": device.device_name or "Browser Push",
        "device_name": device.device_name or "Browser Push",
        "platform": device.platform or "web",
        "device_token": device.device_token,
        "status": "connected",
        "is_connected": True,
        "last_active": device.last_active.isoformat() if device.last_active else None,
        "can_disconnect": True,
    }


class DeviceRegistryService:
    @staticmethod
    def list_devices(db, user: User) -> dict[str, Any]:
        devices: list[dict[str, Any]] = []

        from services.google_fit_service import GoogleFitService

        google_fit_status = GoogleFitService.get_status(db, user)
        if google_fit_status.get("connected"):
            devices.append(
                {
                    "id": "google-fit",
                    "kind": "integration",
                    "provider": "google-fit",
                    "name": "Google Fit",
                    "device_name": "Google Fit",
                    "platform": "wearable",
                    "status": "connected",
                    "is_connected": True,
                    "last_active": google_fit_status.get("last_synced_at"),
                    "last_synced_at": google_fit_status.get("last_synced_at"),
                    "can_disconnect": True,
                }
            )

        push_devices = (
            db.query(NotificationDevice)
            .filter(NotificationDevice.user_id == user.id)
            .order_by(NotificationDevice.last_active.desc())
            .all()
        )
        devices.extend(_serialize_push_device(device) for device in push_devices)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {"devices": devices},
            "last_updated": devices[0]["last_active"] if devices else None,
        }

    @staticmethod
    def register_push_subscription(db, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        subscription = dict(payload.get("subscription") or {})
        endpoint = str(subscription.get("endpoint") or "").strip()
        if not endpoint:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push subscription endpoint is required.")

        device = (
            db.query(NotificationDevice)
            .filter(NotificationDevice.device_token == endpoint)
            .first()
        )
        if device is None:
            device = NotificationDevice(
                user_id=user.id,
                device_token=endpoint,
            )
            db.add(device)

        device.user_id = user.id
        device.device_name = payload.get("device_name") or device.device_name or "Browser Push"
        device.platform = str(payload.get("platform") or device.platform or "web")
        device.subscription = subscription
        device.last_active = _utc_now()
        db.commit()
        db.refresh(device)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": _serialize_push_device(device),
            "last_updated": device.last_active.isoformat() if device.last_active else None,
        }

    @staticmethod
    def unregister_current_push_subscription(db, user: User, endpoint: str) -> dict[str, Any]:
        normalized_endpoint = str(endpoint or "").strip()
        if not normalized_endpoint:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push subscription endpoint is required.")

        deleted_count = (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.user_id == user.id,
                NotificationDevice.device_token == normalized_endpoint,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {"deleted_count": deleted_count},
            "last_updated": None,
        }

    @staticmethod
    def disconnect_device(db, user: User, device_id: str) -> dict[str, Any]:
        if device_id == "google-fit":
            from services.google_fit_service import GoogleFitService

            payload = GoogleFitService.disconnect(db, user)
            return {
                "success": True,
                "status": "ready",
                "source": "db",
                "error": None,
                "data": payload,
                "last_updated": None,
            }

        try:
            device_uuid = uuid.UUID(str(device_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device id") from exc

        deleted_count = (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.id == device_uuid,
                NotificationDevice.user_id == user.id,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        if not deleted_count:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {"deleted_count": deleted_count},
            "last_updated": None,
        }
