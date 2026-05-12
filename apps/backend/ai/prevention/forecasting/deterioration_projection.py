from __future__ import annotations

from ..utils import clamp, safe_dict, safe_list, safe_text


class DeteriorationProjection:
    @staticmethod
    def project(monitoring_state: dict, context: dict) -> dict:
        signals = safe_list(monitoring_state.get("signals"))
        top_risk = max((float(safe_dict(item).get("risk_score") or 0.0) for item in signals), default=0.0)
        acceleration = max((float(safe_dict(item).get("acceleration") or 0.0) for item in signals), default=0.0)
        persistence = max((float(safe_dict(item).get("persistence_days") or 0.0) for item in signals), default=0.0)
        current_risk = float(monitoring_state.get("overall_risk") or 0.0)
        risk_24h = clamp(current_risk + acceleration * 8.0 + persistence * 1.1)
        risk_72h = clamp(max(risk_24h, top_risk) + acceleration * 14.0 + persistence * 1.8)
        risk_7d = clamp(risk_72h + acceleration * 22.0 + persistence * 2.4)
        likely_domain = safe_text(safe_dict(signals[0]).get("domain")) if signals else "general"
        summary = (
            f"Short-term deterioration risk is concentrated around {likely_domain.replace('_', ' ')} and may keep building over the next several days."
            if risk_72h >= 55.0
            else "Projected deterioration risk is present but not rapidly accelerating."
        )
        return {
            "summary": summary,
            "dominant_domain": likely_domain,
            "outlook": "deteriorating" if risk_72h >= 60.0 else "watchful" if risk_24h >= 40.0 else "stable",
            "horizons": {
                "24h": {"projected_risk": round(risk_24h, 4)},
                "72h": {"projected_risk": round(risk_72h, 4)},
                "7d": {"projected_risk": round(risk_7d, 4)},
            },
        }
