from __future__ import annotations

from datetime import datetime, timezone
import logging
import math
from pathlib import Path
import sys
import warnings
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pipelines.ml_pipeline.data_loader import OUTPUT_COLUMNS, load_training_dataframe
from pipelines.ml_pipeline.paths import (
    DEFAULT_MODEL_DIR,
    DEFAULT_MODEL_PATH,
    DISEASE_MODEL_PATHS,
    LEGACY_DEFAULT_MODEL_PATH,
    LEGACY_DISEASE_MODEL_PATHS,
)
from pipelines.ml_pipeline.preprocess import MODEL_TYPES, normalize_model_type, preprocess_for_model
from pipelines.ml_pipeline.utils import should_use_gpu

MODEL_VERSION = "xgb_isotonic_realdata_v2"
CALIBRATION_METHOD = "isotonic"
SCALING_METHOD = "standard"
MIN_TRAINING_ROWS = 21
CLINICAL_ANCHOR_PREFIX = "clinical-anchor-"

warnings.filterwarnings("ignore", message="X does not have valid feature names.*")

logger = logging.getLogger("uvicorn.error")
_GPU_FALLBACK_TRIGGERED = False


def _missing_value_summary(dataframe: pd.DataFrame) -> dict[str, int]:
    tracked_columns = [column for column in OUTPUT_COLUMNS if column in dataframe.columns]
    return {column: int(dataframe[column].isna().sum()) for column in tracked_columns}


def _xgb_runtime_params(use_gpu: bool) -> dict[str, Any]:
    if use_gpu:
        return {
            "tree_method": "gpu_hist",
            "predictor": "gpu_predictor",
        }
    return {"tree_method": "hist"}


def _gpu_mode(use_gpu: bool) -> bool:
    return bool(use_gpu and not _GPU_FALLBACK_TRIGGERED)


def _mark_gpu_fallback(model_type: str, stage: str, exc: Exception) -> None:
    global _GPU_FALLBACK_TRIGGERED

    _GPU_FALLBACK_TRIGGERED = True
    logger.warning(
        "ML GPU fallback triggered | model_type=%s stage=%s fallback=cpu tree_method=hist error=%s",
        model_type,
        stage,
        exc,
    )
    print(f"[{model_type}] GPU fallback triggered during {stage}; retrying with CPU hist.")


def _build_xgb_classifier(*, use_gpu: bool | None = None) -> XGBClassifier:
    gpu_mode = should_use_gpu() if use_gpu is None else _gpu_mode(use_gpu)
    return XGBClassifier(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=5,
        min_child_weight=1,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        **_xgb_runtime_params(gpu_mode),
        random_state=42,
        n_jobs=1,
    )


def _build_scaled_xgb_pipeline(*, use_gpu: bool | None = None) -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("xgb", _build_xgb_classifier(use_gpu=use_gpu)),
        ]
    )


def _calibration_cv(targets: pd.Series) -> int:
    counts = targets.value_counts()
    if len(counts) < 2:
        raise ValueError("Calibrated training requires both positive and negative labels.")

    smallest_class = int(counts.min())
    if smallest_class < 2:
        raise ValueError("Isotonic calibration requires at least two samples in each class.")
    return min(3, smallest_class)


def _calibrated_classifier(targets: pd.Series, *, use_gpu: bool | None = None) -> CalibratedClassifierCV:
    return CalibratedClassifierCV(
        estimator=_build_scaled_xgb_pipeline(use_gpu=use_gpu),
        method=CALIBRATION_METHOD,
        cv=_calibration_cv(targets),
    )


def _fit_calibrated_classifier(
    model_type: str,
    features: pd.DataFrame,
    targets: pd.Series,
    *,
    use_gpu: bool,
    stage: str,
) -> CalibratedClassifierCV:
    model = _calibrated_classifier(targets, use_gpu=use_gpu)
    try:
        model.fit(features.to_numpy(dtype=float), targets.to_numpy())
        return model
    except Exception as exc:
        if not _gpu_mode(use_gpu):
            raise
        _mark_gpu_fallback(model_type, stage, exc)
        cpu_model = _calibrated_classifier(targets, use_gpu=False)
        cpu_model.fit(features.to_numpy(dtype=float), targets.to_numpy())
        return cpu_model


def _fit_xgb_classifier(
    model_type: str,
    features: np.ndarray,
    targets: pd.Series,
    *,
    use_gpu: bool,
    stage: str,
) -> XGBClassifier:
    model = _build_xgb_classifier(use_gpu=use_gpu)
    try:
        model.fit(features, targets.to_numpy())
        return model
    except Exception as exc:
        if not _gpu_mode(use_gpu):
            raise
        _mark_gpu_fallback(model_type, stage, exc)
        cpu_model = _build_xgb_classifier(use_gpu=False)
        cpu_model.fit(features, targets.to_numpy())
        return cpu_model


def _positive_probabilities(model: Any, features: pd.DataFrame) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names.*")
        probabilities = np.asarray(model.predict_proba(features.to_numpy(dtype=float)), dtype=float)

    classes = list(getattr(model, "classes_", []))
    if 1 in classes:
        return probabilities[:, classes.index(1)]
    if len(classes) == 1:
        return np.ones(probabilities.shape[0], dtype=float) if classes[0] == 1 else np.zeros(probabilities.shape[0], dtype=float)
    if probabilities.shape[1] > 1:
        return probabilities[:, 1]
    return probabilities[:, 0]


def _auc_or_nan(targets: pd.Series, probabilities: np.ndarray) -> float:
    if len(set(int(value) for value in targets)) <= 1:
        return math.nan
    return float(roc_auc_score(targets, probabilities))


def _feature_importance_summary(model: XGBClassifier, feature_names: tuple[str, ...]) -> list[dict[str, Any]]:
    raw_importances = getattr(model, "feature_importances_", None)
    if raw_importances is None:
        return []

    rows = [
        {"feature": feature_name, "importance": float(importance)}
        for feature_name, importance in zip(feature_names, raw_importances)
    ]
    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows


def _split_training_data(
    features: pd.DataFrame,
    targets: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, bool]:
    label_counts = targets.value_counts()
    if len(features) < 10 or len(label_counts) < 2 or int(label_counts.min()) < 3:
        return features, features, targets, targets, False

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=0.2,
        random_state=42,
        stratify=targets,
    )
    return X_train, X_test, y_train, y_test, True


def _print_auc(model_type: str, model: Any, features: pd.DataFrame, targets: pd.Series, is_holdout: bool) -> float:
    probabilities = _positive_probabilities(model, features)
    auc = _auc_or_nan(targets, probabilities)
    label = "Validation AUC" if is_holdout else "Training AUC"
    if math.isnan(auc):
        print(f"[{model_type}] {label}: nan (undefined because labels contain one class)")
    else:
        print(f"[{model_type}] {label}: {auc:.4f}")
    return auc


def _fit_for_metrics(
    model_type: str,
    features: pd.DataFrame,
    targets: pd.Series,
    *,
    use_gpu: bool,
) -> tuple[float, bool]:
    X_train, X_test, y_train, y_test, is_holdout = _split_training_data(features, targets)
    if not is_holdout:
        return math.nan, False

    metric_model = _fit_calibrated_classifier(
        model_type,
        X_train,
        y_train,
        use_gpu=use_gpu,
        stage="validation-metrics",
    )
    return _print_auc(model_type, metric_model, X_test, y_test, is_holdout=True), True


def _write_legacy_artifact(model_type: str, artifact: dict[str, Any]) -> None:
    LEGACY_DISEASE_MODEL_PATHS[model_type].parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, LEGACY_DISEASE_MODEL_PATHS[model_type])
    if model_type == "diabetes":
        joblib.dump(artifact, LEGACY_DEFAULT_MODEL_PATH)


def _clinical_anchor_count(dataframe: pd.DataFrame) -> int:
    if "user_id" not in dataframe.columns:
        return 0
    return int(dataframe["user_id"].astype(str).str.startswith(CLINICAL_ANCHOR_PREFIX).sum())


def _label_readiness(dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
    readiness: dict[str, dict[str, Any]] = {}
    for model_type in MODEL_TYPES:
        try:
            _, targets, _ = preprocess_for_model(dataframe, model_type)
        except ValueError as exc:
            readiness[model_type] = {"error": str(exc), "label_counts": {}}
            continue

        label_counts = {int(label): int(count) for label, count in targets.value_counts().sort_index().items()}
        readiness[model_type] = {"error": None, "label_counts": label_counts}
    return readiness


def _assert_all_models_trainable(dataframe: pd.DataFrame) -> None:
    readiness = _label_readiness(dataframe)
    print(f"Label readiness: {readiness}")

    errors: list[str] = []
    if len(dataframe) < MIN_TRAINING_ROWS:
        errors.append(f"dataset has {len(dataframe)} rows; at least {MIN_TRAINING_ROWS} are required")

    for model_type, summary in readiness.items():
        label_counts = summary["label_counts"]
        if summary["error"]:
            errors.append(f"{model_type}: {summary['error']}")
        elif len(label_counts) < 2:
            errors.append(f"{model_type}: target contains one class only ({label_counts})")
        elif min(label_counts.values()) < 2:
            errors.append(f"{model_type}: isotonic calibration needs at least two rows per class ({label_counts})")

    if errors:
        raise ValueError(
            "Training aborted before writing artifacts because the ML dataset is not valid. "
            f"Details: {'; '.join(errors)}"
        )


def _train_single_model(dataframe: pd.DataFrame, model_type: str, output_path: Path) -> dict[str, Any]:
    normalized_type = normalize_model_type(model_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features, targets, feature_names = preprocess_for_model(dataframe, normalized_type)
    label_counts = {int(label): int(count) for label, count in targets.value_counts().sort_index().items()}
    if len(features) < MIN_TRAINING_ROWS:
        raise ValueError(
            f"[{normalized_type}] Training aborted: dataset has {len(features)} rows; "
            f"at least {MIN_TRAINING_ROWS} are required."
        )
    if len(label_counts) < 2:
        raise ValueError(
            f"[{normalized_type}] Training aborted: target contains one class only ({label_counts})."
        )
    if min(label_counts.values()) < 2:
        raise ValueError(
            f"[{normalized_type}] Training aborted: isotonic calibration needs at least two rows per class ({label_counts})."
        )

    print(f"[{normalized_type}] Training rows: {len(features)}")
    print(f"[{normalized_type}] Label distribution: {label_counts}")
    use_gpu = should_use_gpu()
    print(f"[{normalized_type}] XGBoost GPU mode: {'enabled' if use_gpu else 'disabled'}")

    validation_auc, used_holdout = _fit_for_metrics(normalized_type, features, targets, use_gpu=use_gpu)

    shap_transformer = StandardScaler()
    scaled_features = shap_transformer.fit_transform(features.to_numpy(dtype=float))
    shap_model = _fit_xgb_classifier(
        normalized_type,
        scaled_features,
        targets,
        use_gpu=use_gpu,
        stage="shap-model",
    )

    classifier = _fit_calibrated_classifier(
        normalized_type,
        features,
        targets,
        use_gpu=use_gpu,
        stage="classifier",
    )

    if not used_holdout:
        validation_auc = _print_auc(normalized_type, classifier, features, targets, is_holdout=False)

    feature_importance = _feature_importance_summary(shap_model, feature_names)
    print(f"[{normalized_type}] Feature importance: {feature_importance}")

    artifact = {
        "model": classifier,
        "shap_model": shap_model,
        "features": list(feature_names),
        "version": MODEL_VERSION,
        "model_version": MODEL_VERSION,
        "type": normalized_type,
        "label": f"{normalized_type}_risk",
        "positive_class_index": 1,
        "shap_transformer": shap_transformer,
        "training_summary": {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "model_family": "xgboost",
            "calibration_method": CALIBRATION_METHOD,
            "scaling_method": SCALING_METHOD,
            "auc": None if math.isnan(validation_auc) else round(validation_auc, 6),
            "auc_split": "holdout" if used_holdout else "training",
            "label_counts": label_counts,
            "feature_importance": feature_importance,
            "synthetic_labels": False,
            "clinical_anchor_rows": _clinical_anchor_count(dataframe),
        },
    }
    joblib.dump(artifact, output_path)
    print(f"[{normalized_type}] Saved model artifact to {output_path.as_posix()}")
    _write_legacy_artifact(normalized_type, artifact)
    return artifact


def train_all_models(output_dir: str | Path | None = None) -> dict[str, Path]:
    model_dir = Path(output_dir) if output_dir is not None else DEFAULT_MODEL_DIR
    model_dir.mkdir(parents=True, exist_ok=True)

    dataframe = load_training_dataframe()
    print(f"Dataset shape: {dataframe.shape}")
    missing_before = _missing_value_summary(dataframe)
    print(f"Missing values after loader cleaning: {missing_before}")
    _assert_all_models_trainable(dataframe)

    output_paths = {
        model_type: (model_dir / DISEASE_MODEL_PATHS[model_type].name)
        for model_type in MODEL_TYPES
    }
    for model_type in MODEL_TYPES:
        _train_single_model(dataframe, model_type, output_paths[model_type])

    return output_paths


def _infer_model_type_from_path(path: Path) -> str:
    lowered_name = path.name.lower()
    if "cardio" in lowered_name or "cardiovascular" in lowered_name:
        return "cardio"
    if "sleep" in lowered_name:
        return "sleep"
    return "diabetes"


def train_and_save_model(output_path: str | Path | None = None, model_type: str | None = None) -> Path:
    if output_path is None and model_type is None:
        train_all_models()
        return DEFAULT_MODEL_PATH

    normalized_type = normalize_model_type(model_type or _infer_model_type_from_path(Path(output_path or DEFAULT_MODEL_PATH)))
    model_path = Path(output_path) if output_path is not None else DISEASE_MODEL_PATHS[normalized_type]
    model_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = load_training_dataframe()
    print(f"Dataset shape: {dataframe.shape}")
    missing_before = _missing_value_summary(dataframe)
    print(f"Missing values after loader cleaning: {missing_before}")
    _train_single_model(dataframe, normalized_type, model_path)
    return model_path


def ensure_model_artifact(output_path: str | Path | None = None, model_type: str | None = None) -> Path:
    normalized_type = normalize_model_type(model_type or _infer_model_type_from_path(Path(output_path or DEFAULT_MODEL_PATH)))
    model_path = Path(output_path) if output_path is not None else DISEASE_MODEL_PATHS[normalized_type]
    if model_path.is_file():
        return model_path
    return train_and_save_model(model_path, model_type=normalized_type)


def main() -> None:
    train_and_save_model()


if __name__ == "__main__":
    main()
