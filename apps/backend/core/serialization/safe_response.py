from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketState

from .json_safe import make_json_safe, serialization_debug_enabled

logger = logging.getLogger(__name__)


def _degraded_last_updated(content: Any) -> str:
    if isinstance(content, Mapping):
        last_updated = content.get("last_updated")
        if last_updated is not None:
            return str(last_updated)
        data = content.get("data")
        if isinstance(data, Mapping) and data.get("last_updated") is not None:
            return str(data.get("last_updated"))
    return datetime.now(timezone.utc).isoformat()


def _build_degraded_payload(content: Any, *, channel: str) -> dict[str, Any]:
    last_updated = _degraded_last_updated(content)
    if isinstance(content, Mapping):
        payload_type = str(content.get("type") or "serialization.degraded")
        user_id = content.get("user_id")
        return {
            "type": payload_type,
            "user_id": str(user_id) if user_id is not None else None,
            "data": {
                "status": "degraded",
                "error": "payload_sanitized",
                "message": "Realtime update temporarily sanitized.",
                "channel": channel,
                "last_updated": last_updated,
            },
            "last_updated": last_updated,
            "meta": {
                "degraded": True,
                "channel": channel,
            },
        }
    return {
        "type": "serialization.degraded",
        "data": {
            "status": "degraded",
            "error": "payload_sanitized",
            "message": "Realtime update temporarily sanitized.",
            "channel": channel,
            "last_updated": last_updated,
        },
        "last_updated": last_updated,
        "meta": {
            "degraded": True,
            "channel": channel,
        },
    }


def normalize_outbound_payload(content: Any, *, channel: str) -> Any:
    if serialization_debug_enabled():
        logger.debug(
            "[SERIALIZATION] normalizing outbound payload | channel=%s root_type=%s",
            channel,
            type(content).__name__,
        )
    try:
        safe_content = make_json_safe(content)
        json.dumps(safe_content, allow_nan=False)
        if serialization_debug_enabled():
            logger.debug("[SERIALIZATION NORMALIZED] outbound payload ready | channel=%s", channel)
        return safe_content
    except Exception:
        logger.exception(
            "[SERIALIZATION] outbound normalization failed | channel=%s root_type=%s",
            channel,
            type(content).__name__,
        )
        degraded_payload = _build_degraded_payload(content, channel=channel)
        try:
            json.dumps(degraded_payload, allow_nan=False)
        except Exception:
            degraded_payload = {
                "type": "serialization.degraded",
                "data": {
                    "status": "degraded",
                    "error": "payload_sanitized",
                    "message": "Realtime update temporarily sanitized.",
                    "channel": channel,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "meta": {
                    "degraded": True,
                    "channel": channel,
                },
            }
        return degraded_payload


class SafeJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return super().render(normalize_outbound_payload(content, channel="response"))


def safe_json_dumps(content: Any, *, channel: str = "websocket", **json_kwargs: Any) -> str:
    payload = normalize_outbound_payload(content, channel=channel)
    json_kwargs.setdefault("allow_nan", False)
    return json.dumps(payload, **json_kwargs)


def is_socket_alive(websocket: WebSocket) -> bool:
    try:
        return (
            websocket.client_state == WebSocketState.CONNECTED
            and websocket.application_state == WebSocketState.CONNECTED
        )
    except AttributeError:
        return not bool(getattr(websocket, "closed", False))
    except Exception:
        return False


async def websocket_send_json_safe(
    websocket: WebSocket,
    payload: Any,
    *,
    channel: str = "websocket",
    context: str = "websocket",
) -> bool:
    if not is_socket_alive(websocket):
        logger.info("[WS CLOSED] action=skip_send context=%s", context)
        return False

    try:
        await websocket.send_text(safe_json_dumps(payload, channel=channel))
        return True
    except WebSocketDisconnect:
        logger.info("[WS CLOSED] action=disconnect_during_send context=%s", context)
    except RuntimeError as exc:
        logger.warning("[WS CLOSED] action=runtime_error context=%s error=%s", context, exc)
    except Exception:
        logger.exception("[WS CLOSED] action=send_failed context=%s", context)
    return False
