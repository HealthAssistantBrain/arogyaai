from __future__ import annotations

from typing import Any

from ..correlation import CausalPatternEngine, CrossMetricAnalysis, DeteriorationCorrelation, SignalCorrelation
from ..reasoners import (
    AnomalyReasoner,
    BehavioralReasoner,
    CardiovascularReasoner,
    FatigueReasoner,
    MetabolicReasoner,
    RecoveryReasoner,
    RespiratoryReasoner,
    SleepReasoner,
    TrendReasoner,
)
from ..schemas import NarrativeContext, ReasoningCard


class PhysiologicalReasoner:
    def __init__(self) -> None:
        self.domain_reasoners = [
            CardiovascularReasoner(),
            MetabolicReasoner(),
            RecoveryReasoner(),
            SleepReasoner(),
            RespiratoryReasoner(),
            BehavioralReasoner(),
            AnomalyReasoner(),
            TrendReasoner(),
            FatigueReasoner(),
        ]
        self.signal_correlation = SignalCorrelation()
        self.cross_metric = CrossMetricAnalysis()
        self.causal_engine = CausalPatternEngine()
        self.deterioration = DeteriorationCorrelation()

    def analyze(self, context: NarrativeContext, *, temporal: dict[str, Any]) -> dict[str, Any]:
        cards: list[ReasoningCard] = []
        for reasoner in self.domain_reasoners:
            cards.extend(reasoner.analyze(context))
        correlations = self.signal_correlation.analyze(context)
        causal_cards = self.causal_engine.interpret(context, correlations)
        cross_metric = self.cross_metric.analyze(context, correlations=causal_cards, physiological_cards=cards)
        deterioration = self.deterioration.analyze(context, temporal=temporal, causal_cards=causal_cards)
        return {
            "cards": cards,
            "causal_cards": causal_cards,
            "cross_metric": cross_metric,
            "deterioration": deterioration,
        }
