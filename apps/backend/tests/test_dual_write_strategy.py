from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy.exc import InvalidRequestError
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.storage_pipeline.service import StoragePipelineService
from services.user_data_service import UserDataService


def _baseline_db() -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    return db


def _vitals_db() -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def test_store_baseline_metrics_mirrors_to_analytics_in_dual_write_mode():
    primary_db = _baseline_db()
    analytics_db = _baseline_db()
    user = SimpleNamespace(id=uuid4())
    now = datetime.now(timezone.utc)

    @contextmanager
    def _analytics_scope():
        yield analytics_db

    with patch("pipelines.storage_pipeline.service.analytics_dual_write_enabled", return_value=True), patch(
        "pipelines.storage_pipeline.service.analytics_session_scope",
        _analytics_scope,
    ):
        persisted = StoragePipelineService.store_baseline_metrics(
            primary_db,
            user,
            [
                {
                    "metric_name": "health_score_baseline",
                    "mean_7d": 82.5,
                    "mean_30d": 82.5,
                    "std_dev": 0,
                    "sample_count": 1,
                    "window_start": now,
                    "window_end": now,
                    "metric_payload": {"source": "test"},
                }
            ],
        )

    assert len(persisted) == 1
    primary_db.commit.assert_called_once()
    analytics_db.commit.assert_called_once()


def test_store_vitals_mirrors_to_analytics_in_dual_write_mode():
    primary_db = _vitals_db()
    analytics_db = _vitals_db()
    user = SimpleNamespace(id=uuid4())
    timestamp = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "heart_rate",
            "value": 72.0,
            "unit": "bpm",
            "timestamp": timestamp,
            "source": "google_fit",
        }
    ]

    @contextmanager
    def _analytics_scope():
        yield analytics_db

    with patch("services.user_data_service.analytics_dual_write_enabled", return_value=True), patch(
        "services.user_data_service.analytics_session_scope",
        _analytics_scope,
    ), patch(
        "services.user_data_service.IngestionPipelineService.normalize_vital_records",
        return_value=records,
    ):
        saved = UserDataService.store_vitals(primary_db, user, records)

    assert len(saved) == 1
    primary_db.commit.assert_called_once()
    analytics_db.commit.assert_called_once()


def test_store_wearable_metrics_keeps_primary_write_when_analytics_mirror_fails():
    primary_db = _vitals_db()
    user = SimpleNamespace(id=uuid4())
    timestamp = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    records = [
        {
            "metric_type": "spo2",
            "value": 97.0,
            "unit": "%",
            "timestamp": timestamp,
            "source": "google_fit",
            "metadata": {"source": "test"},
        }
    ]

    with patch("services.user_data_service.analytics_dual_write_enabled", return_value=True), patch(
        "services.user_data_service.analytics_session_scope",
        side_effect=RuntimeError("analytics unavailable"),
    ):
        saved = UserDataService.store_wearable_metrics(primary_db, user, records)

    assert len(saved) == 1
    primary_db.commit.assert_called_once()


def test_store_risk_score_mirrors_prediction_history_to_analytics():
    primary_db = MagicMock()
    primary_db.query.return_value.filter.return_value.one_or_none.return_value = None
    analytics_db = MagicMock()
    analytics_db.query.return_value.filter.return_value.one_or_none.return_value = None
    user = SimpleNamespace(id=uuid4())

    @contextmanager
    def _analytics_scope():
        yield analytics_db

    with patch("pipelines.storage_pipeline.service.analytics_dual_write_enabled", return_value=True), patch(
        "pipelines.storage_pipeline.service.analytics_session_scope",
        _analytics_scope,
    ):
        record = StoragePipelineService.store_risk_score(
            primary_db,
            user,
            risk_payload={"overall_score": 42.5, "recommendations": []},
            model_version="cardio-v2",
            source="ml",
            status="ready",
            run_id="run-123",
        )

    assert record.model_version == "cardio-v2"
    assert record.run_id == "run-123"
    primary_db.commit.assert_called_once()
    analytics_db.commit.assert_called_once()


def test_store_health_score_dual_write_does_not_refresh_primary_session_user_in_analytics_mirror():
    primary_db = MagicMock()
    primary_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    analytics_db = MagicMock()
    analytics_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    user = SimpleNamespace(id=uuid4(), health_score=81.0, score_change_percent=0.0)

    def _analytics_refresh(instance):
        if instance is user:
            raise InvalidRequestError("Instance '<User ...>' is not persistent within this Session")

    analytics_db.refresh.side_effect = _analytics_refresh

    @contextmanager
    def _analytics_scope():
        yield analytics_db

    with patch("pipelines.storage_pipeline.service.analytics_dual_write_enabled", return_value=True), patch(
        "pipelines.storage_pipeline.service.analytics_session_scope",
        _analytics_scope,
    ), patch("pipelines.storage_pipeline.service.logger.exception") as log_exception:
        record = StoragePipelineService.store_health_score(
            primary_db,
            user,
            risk_score=None,
            health_payload={"score": 84.5, "risk_component": 30.0},
        )

    assert float(record.score) == 84.5
    primary_db.commit.assert_called_once()
    analytics_db.commit.assert_called_once()
    log_exception.assert_not_called()
    assert all(call.args[0] is not user for call in analytics_db.refresh.call_args_list)
