from __future__ import annotations

import json

from core.config import settings

try:
    from pywebpush import WebPushException, webpush
except ModuleNotFoundError:  # pragma: no cover
    WebPushException = Exception
    webpush = None


class PushSubscriptionExpiredError(RuntimeError):
    pass


class PushService:
    @staticmethod
    def _status_code_from_exception(exc: Exception) -> int | None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        try:
            return int(status_code) if status_code is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def send_push(subscription: dict, title: str, message: str, *, url: str = "/notifications", data: dict | None = None) -> dict:
        if webpush is None:
            raise RuntimeError("pywebpush is not installed.")
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            raise RuntimeError("VAPID keys are not configured.")

        payload = {
            "title": title,
            "body": message,
            "url": url,
            **(data or {}),
        }

        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
        except WebPushException as exc:
            status_code = PushService._status_code_from_exception(exc)
            if status_code in {404, 410}:
                raise PushSubscriptionExpiredError("Push subscription has expired.") from exc
            raise

        return {"provider": "webpush", "status": "sent"}
