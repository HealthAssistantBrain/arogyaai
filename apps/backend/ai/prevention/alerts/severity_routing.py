from __future__ import annotations


class SeverityRouting:
    @staticmethod
    def route(severity: str, escalation_level: str) -> dict:
        if severity == "critical" or escalation_level == "escalate":
            return {
                "notification_class": "urgent",
                "cadence_minutes": 30,
                "channel": "priority",
            }
        if severity == "warning" or escalation_level == "intervene":
            return {
                "notification_class": "near_real_time",
                "cadence_minutes": 180,
                "channel": "timely",
            }
        return {
            "notification_class": "digest",
            "cadence_minutes": 720,
            "channel": "digest",
        }
