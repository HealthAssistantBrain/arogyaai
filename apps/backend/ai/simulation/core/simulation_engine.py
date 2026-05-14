from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field

from .._shared import GENERATOR_VERSION, SCHEMA_VERSION, log_simulation, simulation_id
from ..datasets.export_pipeline import ExportPipeline
from ..datasets.longitudinal_dataset_generator import LongitudinalDatasetGenerator
from ..schemas.dataset_contract import DatasetContract
from ..schemas.simulation_result import SimulationResult
from .synthetic_population import SyntheticPopulation


class SimulationRequest(BaseModel):
    population_size: int = 9
    duration_days: int = 30
    step_hours: int = 1
    start_at: datetime | None = None
    dataset_version: str = "synthetic_dataset.v1"
    export_root: str | None = None
    lookback_hours: int = 24
    horizon_hours: int = 12
    seed: int = 42


class SimulationEngine:
    def __init__(self) -> None:
        self.generator_version = GENERATOR_VERSION
        self.schema_version = SCHEMA_VERSION

    def _contract(self, request: SimulationRequest) -> DatasetContract:
        return DatasetContract(
            dataset_version=request.dataset_version,
            schema_version=self.schema_version,
            generator_version=self.generator_version,
            generated_at=datetime.now(UTC).isoformat(),
            sequence_window={"duration_days": request.duration_days, "step_hours": request.step_hours},
            feature_manifest=[
                {"name": "rolling_mean_features", "description": "6h and 24h rolling aggregates."},
                {"name": "baseline_delta_features", "description": "Deviation from adaptive user baseline."},
                {"name": "temporal_embeddings", "description": "Hour-of-day cyclic embeddings and day-of-week."},
            ],
            label_manifest=[
                {"name": "anomaly_score", "type": "continuous"},
                {"name": "risk_target", "type": "continuous"},
                {"name": "future_recovery_target", "type": "continuous"},
                {"name": "trajectory_label", "type": "categorical"},
            ],
            sequence_definitions={"longitudinal_sequence": "Hourly physiological stream with daily labs and recovery states."},
            normalization_metadata={"strategy": "baseline-relative feature scaling with bounded ratio normalization"},
            temporal_window_definitions={"lookback_hours": request.lookback_hours, "horizon_hours": request.horizon_hours},
        )

    def generate(self, request: SimulationRequest) -> SimulationResult:
        start_at = request.start_at or (datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(days=request.duration_days))
        hours = max(24, request.duration_days * 24)
        profiles = [profile.model_dump(mode="json") for profile in SyntheticPopulation.build_population(request.population_size, request.seed)]
        bundle = LongitudinalDatasetGenerator.generate(
            profiles=profiles,
            start_at=start_at,
            hours=hours,
            lookback_hours=request.lookback_hours,
            horizon_hours=request.horizon_hours,
        )
        contract = self._contract(request)
        exports: dict[str, Any] = {}
        if request.export_root:
            exports = ExportPipeline.export(
                export_root=request.export_root,
                splits=bundle["splits"],
                manifests=bundle["manifests"],
                contract=contract.model_dump(mode="json"),
            )

        result = SimulationResult(
            run_id=simulation_id(),
            dataset_contract=contract,
            sequences=bundle["sequences"],
            records=bundle["records"],
            feature_vectors=bundle["feature_vectors"],
            temporal_windows=bundle["temporal_windows"],
            splits=bundle["splits"],
            manifests=bundle["manifests"],
            exports=exports,
            validation={
                "medical_realism_scores": {
                    sequence.user_id: sequence.validation.get("medical_realism_score", 0.0)
                    for sequence in bundle["sequences"]
                }
            },
            playback={
                "synthetic_users": [
                    {
                        "user_id": sequence.user_id,
                        "profile": sequence.synthetic_profile,
                        "trajectory": sequence.trajectory_summary,
                        "timeline_preview": sequence.playback["timeline"],
                    }
                    for sequence in bundle["sequences"]
                ]
            },
            metadata={
                "generated_at": datetime.now(UTC).isoformat(),
                "population_size": request.population_size,
                "duration_days": request.duration_days,
                "frontend_support": ["demo_simulations", "trajectory_playback", "anomaly_visualizations", "timeline_simulations", "deterioration_playback"],
            },
        )
        log_simulation("SYNTHETIC DATA", run_id=result.run_id, users=request.population_size, hours=hours)
        return result

    async def async_generate(self, request: SimulationRequest) -> SimulationResult:
        return self.generate(request)

    async def stream_generate(self, request: SimulationRequest) -> AsyncIterator[dict[str, Any]]:
        result = self.generate(request)
        for sequence in result.sequences:
            yield {
                "user_id": sequence.user_id,
                "synthetic_profile": sequence.synthetic_profile,
                "trajectory_summary": sequence.trajectory_summary,
                "records_generated": len(sequence.records),
            }
