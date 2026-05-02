from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_DIR = REPO_ROOT / "models"
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "diabetes_model.pkl"
DISEASE_MODEL_PATHS: dict[str, Path] = {
    "diabetes": DEFAULT_MODEL_DIR / "diabetes_model.pkl",
    "cardio": DEFAULT_MODEL_DIR / "cardio_model.pkl",
    "sleep": DEFAULT_MODEL_DIR / "sleep_model.pkl",
}

LEGACY_MODEL_DIR = REPO_ROOT / "apps" / "backend" / "models"
LEGACY_DEFAULT_MODEL_PATH = LEGACY_MODEL_DIR / "health_model.pkl"
LEGACY_DISEASE_MODEL_PATHS: dict[str, Path] = {
    "diabetes": LEGACY_MODEL_DIR / "health_model_diabetes.pkl",
    "cardio": LEGACY_MODEL_DIR / "health_model_cardio.pkl",
    "sleep": LEGACY_MODEL_DIR / "health_model_sleep.pkl",
}
