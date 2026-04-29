from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pipelines.ml_pipeline.preprocess import FEATURE_NAMES

DEFAULT_MODEL_PATH = REPO_ROOT / "apps" / "backend" / "models" / "diabetes.pkl"


def _build_dummy_dataset(samples: int = 1200) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed=42)

    bmi = rng.normal(27.0, 4.5, size=samples).clip(16.0, 45.0)
    hr_mean_7d = rng.normal(74.0, 10.0, size=samples).clip(45.0, 130.0)
    steps_avg_7d = rng.normal(6800.0, 2600.0, size=samples).clip(500.0, 18000.0)
    sleep_efficiency = rng.normal(77.0, 12.0, size=samples).clip(35.0, 100.0)
    lifestyle_score = rng.normal(62.0, 15.0, size=samples).clip(10.0, 100.0)
    activity_score = rng.normal(58.0, 18.0, size=samples).clip(5.0, 100.0)

    features = np.column_stack(
        [
            bmi,
            hr_mean_7d,
            steps_avg_7d,
            sleep_efficiency,
            lifestyle_score,
            activity_score,
        ]
    )

    logit = (
        0.12 * (bmi - 25.0)
        + 0.035 * (hr_mean_7d - 70.0)
        - 0.00025 * (steps_avg_7d - 7000.0)
        - 0.03 * (sleep_efficiency - 75.0)
        - 0.028 * (lifestyle_score - 60.0)
        - 0.018 * (activity_score - 60.0)
        + rng.normal(0.0, 0.65, size=samples)
    )

    probabilities = 1.0 / (1.0 + np.exp(-logit))
    targets = rng.binomial(1, probabilities)
    return features, targets


def train_and_save_model(output_path: str | Path | None = None) -> Path:
    model_path = Path(output_path) if output_path is not None else DEFAULT_MODEL_PATH
    model_path.parent.mkdir(parents=True, exist_ok=True)

    features, targets = _build_dummy_dataset()
    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=8,
        min_samples_leaf=4,
        random_state=42,
    )
    model.fit(features, targets)

    artifact = {
        "model": model,
        "feature_names": list(FEATURE_NAMES),
        "model_version": f"diabetes-rf-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        "label": "diabetes_risk",
        "positive_class_index": 1,
        "training_summary": {
            "dataset": "synthetic_bootstrap",
            "sample_count": int(len(targets)),
            "positive_rate": float(np.mean(targets)),
        },
    }
    joblib.dump(artifact, model_path)
    return model_path


def ensure_model_artifact(output_path: str | Path | None = None) -> Path:
    model_path = Path(output_path) if output_path is not None else DEFAULT_MODEL_PATH
    if model_path.is_file():
        return model_path
    return train_and_save_model(model_path)


def main() -> None:
    model_path = train_and_save_model()
    print(f"Saved ML model artifact to {model_path.as_posix()}")


if __name__ == "__main__":
    main()
