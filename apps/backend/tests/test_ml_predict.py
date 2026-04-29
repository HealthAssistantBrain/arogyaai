from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.ml_pipeline.model_loader import LoadedModel
from pipelines.ml_pipeline.predict import predict_with_loaded_model


class _TrackingModel:
    n_features_in_ = 6

    def __init__(self) -> None:
        self.seen_rows: list[list[float]] = []

    def predict_proba(self, rows):
        self.seen_rows = [list(row) for row in rows]
        return [[0.15, 0.85]]


def test_predict_with_loaded_model_trims_legacy_extra_features():
    model = _TrackingModel()
    loaded_model = LoadedModel(
        model=model,
        path="memory://test-model",
        feature_names=(
            "bmi",
            "hr_mean_7d",
            "steps_avg_7d",
            "sleep_efficiency",
            "lifestyle_score",
            "activity_score",
            "glucose",
            "cholesterol",
        ),
    )

    result = predict_with_loaded_model([24.5, 68.0, 7200.0, 81.0, 76.5, 60.0, 104.0, 172.0], loaded_model)

    assert model.seen_rows == [[24.5, 68.0, 7200.0, 81.0, 76.5, 60.0]]
    assert result.probability == 0.85
    assert result.confidence == 0.85
