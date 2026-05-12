from __future__ import annotations

from typing import Any


class EmergencyGuard:
    def apply(
        self,
        payload: dict[str, Any],
        *,
        emergency: dict[str, Any],
        emergency_message: str,
    ) -> dict[str, Any]:
        if not emergency.get("detected"):
            return {"payload": payload, "flags": [], "modified": False}
        updated = dict(payload)
        updated["message"] = emergency_message
        updated["summary"] = emergency_message
        updated["clinical_summary"] = emergency_message
        recommendations = updated.get("recommendations") if isinstance(updated.get("recommendations"), list) else []
        injected = [
            "Call local emergency services now.",
            "Do not wait for this chat if symptoms are severe, sudden, or worsening.",
        ]
        for item in reversed(injected):
            if item not in recommendations:
                recommendations.insert(0, item)
        updated["recommendations"] = recommendations[:4]
        safety_notes = updated.get("safety_notes") if isinstance(updated.get("safety_notes"), list) else []
        if emergency_message not in safety_notes:
            safety_notes.insert(0, emergency_message)
        updated["safety_notes"] = safety_notes[:3]
        updated["warning_banner"] = emergency_message
        return {
            "payload": updated,
            "flags": ["emergency_detected"],
            "modified": True,
        }
