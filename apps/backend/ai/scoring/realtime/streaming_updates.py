from __future__ import annotations

import logging

from services.dashboard_realtime import _broadcast_current_snapshot, _degraded_dashboard_message, dashboard_connection_manager

logger = logging.getLogger(__name__)

class StreamingUpdatePublisher:
    @staticmethod
    async def publish_user_refresh(user_id: str) -> None:
        try:
            await _broadcast_current_snapshot(user_id)
        except Exception:
            logger.exception("[SCORING] realtime refresh publish failed for user=%s", user_id)
            await dashboard_connection_manager.broadcast(
                str(user_id),
                _degraded_dashboard_message(str(user_id), reason="streaming_refresh_failed"),
            )
