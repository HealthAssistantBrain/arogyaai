from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..utils import safe_dict, safe_list, safe_text


class NotificationIntelligence:
    @staticmethod
    def batch(alerts: list[dict], prior_memory: list[dict]) -> dict:
        threshold = datetime.now(timezone.utc) - timedelta(hours=12)
        seen_titles = {
            safe_text(item.get("trend_note")).lower()
            for item in safe_list(prior_memory)
            if safe_text(item.get("created_at")) and NotificationIntelligence._parse(item.get("created_at")) >= threshold
        }
        delivered: list[dict] = []
        suppressed: list[dict] = []

        for payload in safe_list(alerts):
            alert = dict(safe_dict(payload))
            title = safe_text(alert.get("title")).lower()
            if title in seen_titles and alert.get("severity") != "critical":
                alert["suppressed"] = True
                alert["suppression_reason"] = "recent_duplicate"
                suppressed.append(alert)
                continue
            alert["suppressed"] = False
            alert["deliver_immediately"] = alert.get("severity") == "critical" or alert.get("notification_class") == "urgent"
            delivered.append(alert)

        return {
            "alerts": delivered,
            "suppressed": suppressed,
            "summary": {
                "delivered": len(delivered),
                "suppressed": len(suppressed),
            },
        }

    @staticmethod
    def _parse(value: str) -> datetime:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
