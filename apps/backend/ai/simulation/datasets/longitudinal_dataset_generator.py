from __future__ import annotations

from datetime import datetime
from typing import Any

from .._shared import GENERATOR_VERSION, SCHEMA_VERSION, log_simulation
from ..core.event_generator import EventGenerator
from ..core.physiology_orchestrator import PhysiologyOrchestrator
from ..forecasting.deterioration_forecaster import DeteriorationForecaster
from ..forecasting.recovery_forecaster import RecoveryForecaster
from ..forecasting.trajectory_simulator import TrajectorySimulator
from ..schemas.longitudinal_sequence import LongitudinalSequence
from ..validation import MedicalRealismValidator
from .dataset_builder import DatasetBuilder
from .feature_vector_builder import FeatureVectorBuilder
from .schema_manifest_builder import SchemaManifestBuilder
from .temporal_window_builder import TemporalWindowBuilder
from .training_split_generator import TrainingSplitGenerator


class LongitudinalDatasetGenerator:
    @classmethod
    def generate(
        cls,
        *,
        profiles: list[dict[str, Any]],
        start_at: datetime,
        hours: int,
        lookback_hours: int,
        horizon_hours: int,
    ) -> dict[str, Any]:
        sequences: list[LongitudinalSequence] = []
        all_records: list[dict[str, Any]] = []
        all_feature_vectors: list[dict[str, Any]] = []
        all_temporal_windows: list[dict[str, Any]] = []

        for profile in profiles:
            event_schedule = EventGenerator.generate(profile, start_at.date(), max(1, hours // 24))
            points = PhysiologyOrchestrator.generate_sequence(
                profile=profile,
                start_at=start_at,
                hours=hours,
                event_schedule=event_schedule,
            )
            validation = MedicalRealismValidator.validate(points)
            trajectory_summary = TrajectorySimulator.summarize(points)
            trajectory_summary["deterioration_forecast"] = DeteriorationForecaster.forecast(points)
            trajectory_summary["recovery_forecast"] = RecoveryForecaster.forecast(points)
            records = DatasetBuilder.build_records(profile=profile, points=points)
            feature_vectors = FeatureVectorBuilder.build(profile=profile, points=points)
            temporal_windows = TemporalWindowBuilder.build(feature_vectors, lookback_hours=lookback_hours, horizon_hours=horizon_hours)
            sequence = LongitudinalSequence(
                user_id=profile["user_id"],
                synthetic_profile=profile["synthetic_profile"],
                demographic_profile=profile["demographic_profile"],
                records=records,
                state_points=points,
                trajectory_summary=trajectory_summary,
                feature_vectors=feature_vectors,
                temporal_windows=temporal_windows,
                validation=validation,
                playback={"timeline": points[:: max(1, hours // 40)]},
                metadata={"generator_version": GENERATOR_VERSION, "schema_version": SCHEMA_VERSION},
            )
            sequences.append(sequence)
            all_records.extend(record.model_dump(mode="json") for record in records)
            all_feature_vectors.extend(feature_vectors)
            all_temporal_windows.extend(temporal_windows)

        manifests = SchemaManifestBuilder.build(
            all_records,
            all_feature_vectors,
            {"lookback_hours": lookback_hours, "horizon_hours": horizon_hours},
        )
        splits = TrainingSplitGenerator.split(all_records)
        log_simulation("LONGITUDINAL SEQUENCE", users=len(sequences), records=len(all_records))
        return {
            "sequences": sequences,
            "records": all_records,
            "feature_vectors": all_feature_vectors,
            "temporal_windows": all_temporal_windows,
            "manifests": manifests,
            "splits": splits,
        }
