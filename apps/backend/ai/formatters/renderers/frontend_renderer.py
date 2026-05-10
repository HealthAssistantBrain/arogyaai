from __future__ import annotations

from typing import Any

from ..schemas import ConfidenceBadge, FrontendRenderContract, RenderAlert, RenderCard, StructuredSection


class FrontendRenderer:
    def build(
        self,
        *,
        workflow: str,
        payload: dict[str, Any],
        sections: list[dict[str, Any]],
        warnings: list[Any],
        confidence_score: float,
        confidence_label: str,
        confidence_reasoning: str,
    ) -> FrontendRenderContract:
        structured_sections = [StructuredSection.model_validate(item) for item in sections]
        cards = self._cards(structured_sections)
        alerts = self._alerts(warnings, payload)
        recommendations = self._recommendations(payload)
        insights = self._insights(payload)
        charts = self._charts(workflow, payload)
        timeline = self._timeline(payload)
        badge = ConfidenceBadge(
            label=confidence_label,
            score=round(confidence_score, 4),
            tone=self._badge_tone(confidence_score),
            reasoning=confidence_reasoning,
        )
        return FrontendRenderContract(
            display_mode="conversational_copilot" if workflow in {"chatbot", "ai_insights", "report_summary", "symptom_analysis"} else "clinical_brief",
            sections=structured_sections,
            cards=cards,
            alerts=alerts,
            timeline=timeline,
            recommendations=recommendations,
            insights=insights,
            charts=charts,
            confidence_badge=badge,
        )

    def _cards(self, sections: list[StructuredSection]) -> list[RenderCard]:
        cards: list[RenderCard] = []
        for index, section in enumerate(sections):
            cards.append(
                RenderCard(
                    id=f"section-{index + 1}",
                    type="section",
                    title=section.title,
                    body=section.content,
                    items=section.bullets,
                    tone="alert" if "warning" in section.title.lower() or "risk" in section.title.lower() else "neutral",
                )
            )
        return cards

    def _alerts(self, warnings: list[Any], payload: dict[str, Any]) -> list[RenderAlert]:
        alerts: list[RenderAlert] = []
        for index, item in enumerate(warnings):
            if isinstance(item, dict):
                alerts.append(
                    RenderAlert(
                        id=f"warning-{index + 1}",
                        level=str(item.get("severity") or "medium"),
                        title=str(item.get("code") or "warning").replace("_", " ").title(),
                        message=str(item.get("message") or ""),
                    )
                )
            elif item:
                alerts.append(
                    RenderAlert(
                        id=f"warning-{index + 1}",
                        level="medium",
                        title="Warning",
                        message=str(item),
                    )
                )
        for note in payload.get("safety_notes") or []:
            alerts.append(
                RenderAlert(
                    id=f"safety-{len(alerts) + 1}",
                    level="high",
                    title="Safety Note",
                    message=str(note),
                )
            )
        return alerts

    def _recommendations(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, item in enumerate(payload.get("recommendations") or []):
            if isinstance(item, dict):
                items.append(
                    {
                        "id": f"recommendation-{index + 1}",
                        "title": str(item.get("title") or item.get("test_name") or f"Recommendation {index + 1}"),
                        "detail": str(item.get("detail") or item.get("description") or item.get("reason") or ""),
                        "priority": str(item.get("priority") or "routine"),
                    }
                )
            else:
                text = str(item).strip()
                if text:
                    items.append(
                        {
                            "id": f"recommendation-{index + 1}",
                            "title": f"Recommendation {index + 1}",
                            "detail": text,
                            "priority": "routine",
                        }
                    )
        return items

    def _insights(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        insight_sources = payload.get("drivers") or payload.get("factors") or payload.get("key_drivers") or payload.get("insights") or []
        items: list[dict[str, Any]] = []
        for index, item in enumerate(insight_sources):
            if isinstance(item, dict):
                items.append(
                    {
                        "id": f"insight-{index + 1}",
                        "title": str(item.get("label") or item.get("title") or f"Insight {index + 1}"),
                        "value": item.get("value") or item.get("impact") or item.get("contribution"),
                        "detail": str(item.get("detail") or item.get("description") or item.get("summary") or ""),
                    }
                )
            else:
                text = str(item).strip()
                if text:
                    items.append({"id": f"insight-{index + 1}", "title": text, "value": None, "detail": text})
        return items

    def _charts(self, workflow: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        charts: list[dict[str, Any]] = []
        if isinstance(payload.get("current_risk"), dict) and isinstance(payload.get("simulated_risk"), dict):
            charts.append(
                {
                    "id": "risk-comparison",
                    "type": "comparison_bar",
                    "title": "Current vs Simulated Risk",
                    "series": [
                        {"label": "Current", "values": payload.get("current_risk")},
                        {"label": "Simulated", "values": payload.get("simulated_risk")},
                    ],
                }
            )
        elif isinstance(payload.get("risks"), dict):
            charts.append(
                {
                    "id": "risk-snapshot",
                    "type": "risk_snapshot",
                    "title": "Risk Snapshot",
                    "series": [{"label": "Risk", "values": payload.get("risks")}],
                }
            )
        return charts

    def _timeline(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        timeline = payload.get("timeline", {}).get("events") if isinstance(payload.get("timeline"), dict) else []
        return [item for item in timeline if isinstance(item, dict)]

    def _badge_tone(self, score: float) -> str:
        if score >= 0.8:
            return "positive"
        if score >= 0.6:
            return "watchful"
        if score >= 0.4:
            return "guarded"
        return "cautious"
