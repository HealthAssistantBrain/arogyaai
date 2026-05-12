from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def unique_texts(values: list[Any], *, limit: int = 8) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            text = str(
                value.get("summary")
                or value.get("detail")
                or value.get("description")
                or value.get("title")
                or value.get("name")
                or ""
            ).strip()
        else:
            text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


class MetricSignal(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    label: str
    current: float | None = None
    baseline: float | None = None
    trend: str = "stable"
    unit: str = ""
    status: str = "stable"
    delta: float | None = None
    delta_pct: float | None = None
    lower_is_better: bool = False
    window: str = "7d"
    evidence: list[str] = Field(default_factory=list)

    def formatted_current(self) -> str:
        if self.current is None:
            return ""
        if float(self.current).is_integer():
            return f"{int(self.current)}{self.unit}"
        return f"{self.current:.1f}{self.unit}"

    def formatted_baseline(self) -> str:
        if self.baseline is None:
            return ""
        if float(self.baseline).is_integer():
            return f"{int(self.baseline)}{self.unit}"
        return f"{self.baseline:.1f}{self.unit}"


class NarrativeContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: str = ""
    workflow: str = "ai_insights"
    source: str = "deterministic_reasoning"
    generated_at: str = Field(default_factory=utc_now_iso)
    risk_score: float | None = None
    risk_level: str = "LOW"
    risk_scores: dict[str, float] = Field(default_factory=dict)
    feature_payload: dict[str, Any] = Field(default_factory=dict)
    vitals: dict[str, Any] = Field(default_factory=dict)
    wearable_trends: dict[str, Any] = Field(default_factory=dict)
    forecasting: dict[str, Any] = Field(default_factory=dict)
    clinical_history: dict[str, Any] = Field(default_factory=dict)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    drivers: list[dict[str, Any]] = Field(default_factory=list)
    shap_values: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    labs: list[dict[str, Any]] = Field(default_factory=list)
    ocr_summary: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[Any] = Field(default_factory=list)
    recommendation_plans: list[dict[str, Any]] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    signals: dict[str, MetricSignal] = Field(default_factory=dict)
    longitudinal_summary: dict[str, Any] = Field(default_factory=dict)
    continuity_summary: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    disease_simulation: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    report_summaries: list[dict[str, Any]] = Field(default_factory=list)
    forecast_windows: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def metric(self, *names: str) -> MetricSignal | None:
        for name in names:
            if name in self.signals:
                return self.signals[name]
        return None

    def symptom_present(self, text: str) -> bool:
        needle = str(text or "").strip().lower()
        if not needle:
            return False
        return any(needle in item.lower() for item in self.symptoms)
