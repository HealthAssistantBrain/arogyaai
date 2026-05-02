from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.ml_pipeline.inference import predict_all
from pipelines.ml_pipeline.data_loader import _clean_training_dataframe
from pipelines.ml_pipeline.model_loader import LoadedModel, ModelLoader
from pipelines.ml_pipeline.preprocess import build_target, preprocess_for_model


def test_build_target_uses_exact_disease_rules():
    dataframe = pd.DataFrame(
        [
            {"glucose": 126, "hba1c": 5.4, "systolic_bp": 120, "cholesterol": 180, "sleep_hours": 7, "heart_rate": 70},
            {"glucose": 90, "hba1c": 6.5, "systolic_bp": 140, "cholesterol": 180, "sleep_hours": 4.9, "heart_rate": 70},
            {"glucose": 90, "hba1c": 5.4, "systolic_bp": 120, "cholesterol": 240, "sleep_hours": 7, "heart_rate": 91},
            {"glucose": 90, "hba1c": 5.4, "systolic_bp": 120, "cholesterol": 180, "sleep_hours": 7, "heart_rate": 90},
            {"glucose": None, "hba1c": None, "systolic_bp": None, "cholesterol": None, "sleep_hours": None, "heart_rate": None},
        ]
    )

    diabetes = build_target(dataframe, "diabetes")
    cardio = build_target(dataframe, "cardio")
    sleep = build_target(dataframe, "sleep")

    assert diabetes.iloc[:4].tolist() == [1, 1, 0, 0]
    assert cardio.iloc[:4].tolist() == [0, 1, 1, 0]
    assert sleep.iloc[:4].tolist() == [0, 1, 0, 0]
    assert diabetes.iloc[4] == 0
    assert cardio.iloc[4] == 0
    assert sleep.iloc[4] == 0


def test_preprocess_uses_empty_target_inputs_as_negative_labels():
    dataframe = pd.DataFrame(
        [
            {"age": 40, "bmi": 24.0, "glucose": 126, "hba1c": None},
            {"age": 41, "bmi": 25.0, "glucose": 90, "hba1c": 5.4},
            {"age": 42, "bmi": 26.0, "glucose": None, "hba1c": None},
        ]
    )

    features, target, feature_names = preprocess_for_model(dataframe, "diabetes")

    assert len(features) == 3
    assert target.tolist() == [1, 0, 0]
    assert "bmi" in feature_names


def test_clean_training_dataframe_generates_valid_trainable_labels():
    dataframe = pd.DataFrame(
        [
            {
                "user_id": "real-user-1",
                "age": 44,
                "gender": "male",
                "height": 178,
                "weight": 76,
                "glucose": None,
                "hba1c": None,
                "systolic_bp": None,
                "cholesterol": None,
                "sleep_hours": None,
            }
        ]
    )

    cleaned = _clean_training_dataframe(dataframe)

    assert len(cleaned) > 20
    for column in ("diabetes_label", "cardio_label", "sleep_label"):
        assert not cleaned[column].isna().any()
        assert set(cleaned[column].astype(int).unique()) == {0, 1}


class _ProbModel:
    classes_ = [0, 1]
    n_features_in_ = 1

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, rows):
        return [[1.0 - self.probability, self.probability] for _ in rows]


def test_predict_all_returns_three_disease_risks(monkeypatch):
    loaded_models = {
        "diabetes": LoadedModel(_ProbModel(0.2), "memory://diabetes", feature_names=("age",), model_type="diabetes"),
        "cardio": LoadedModel(_ProbModel(0.4), "memory://cardio", feature_names=("age",), model_type="cardio"),
        "sleep": LoadedModel(_ProbModel(0.6), "memory://sleep", feature_names=("age",), model_type="sleep"),
    }
    monkeypatch.setattr(ModelLoader, "load_all", classmethod(lambda cls, **kwargs: loaded_models))

    assert predict_all({"age": 50}) == {
        "diabetes_risk": 0.2,
        "cardio_risk": 0.4,
        "sleep_risk": 0.6,
    }
