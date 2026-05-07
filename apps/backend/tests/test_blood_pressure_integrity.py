from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import UserVitalSourceEnum  # noqa: E402
from services.dashboard_service import _build_blood_pressure_metric, _build_glucose_metric_payload  # noqa: E402
from services.user_data_service import UserDataService  # noqa: E402


def test_store_vitals_skips_duplicate_blood_pressure_pair():
    timestamp = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "blood_pressure_systolic",
            "value": 122.0,
            "unit": "mmHg",
            "timestamp": timestamp,
            "source": "google_fit",
        },
        {
            "type": "blood_pressure_diastolic",
            "value": 122.0,
            "unit": "mmHg",
            "timestamp": timestamp,
            "source": "google_fit",
        },
    ]
    db = MagicMock()
    user = SimpleNamespace(id=uuid4())

    with patch(
        "services.user_data_service.IngestionPipelineService.normalize_vital_records",
        return_value=records,
    ):
        saved = UserDataService.store_vitals(db, user, records)

    assert saved == []
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_store_vitals_keeps_partial_blood_pressure_row():
    timestamp = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "blood_pressure_systolic",
            "value": 120.0,
            "unit": "mmHg",
            "timestamp": timestamp,
            "source": "google_fit",
        }
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    user = SimpleNamespace(id=uuid4())

    with patch(
        "services.user_data_service.IngestionPipelineService.normalize_vital_records",
        return_value=records,
    ):
        saved = UserDataService.store_vitals(db, user, records)

    assert len(saved) == 1
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_store_wearable_metrics_skips_duplicate_blood_pressure_pair():
    timestamp = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "blood_pressure",
            "value": 122.0,
            "unit": "mmHg",
            "timestamp": timestamp,
            "source": "google_fit",
            "metadata": {"systolic": 122.0, "diastolic": 122.0},
        },
    ]
    db = MagicMock()
    user = SimpleNamespace(id=uuid4())

    saved = UserDataService.store_wearable_metrics(db, user, records)

    assert saved == []
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_store_vitals_persists_glucose_raw_and_normalized_fields():
    timestamp = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "glucose",
            "value": 81.0,
            "unit": "mg/dL",
            "raw_value": 4.5,
            "raw_unit": "mmol/L",
            "normalized_value": 81.0,
            "normalized_unit": "mg/dL",
            "timestamp": timestamp,
            "source": "google_fit",
        }
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    user = SimpleNamespace(id=uuid4())

    with patch(
        "services.user_data_service.IngestionPipelineService.normalize_vital_records",
        return_value=records,
    ):
        saved = UserDataService.store_vitals(db, user, records)

    assert len(saved) == 1
    inserted = db.add.call_args.args[0]
    assert inserted.value == 81.0
    assert inserted.unit == "mg/dL"
    assert inserted.raw_value == 4.5
    assert inserted.raw_unit == "mmol/L"
    assert inserted.normalized_value == 81.0
    assert inserted.normalized_unit == "mg/dL"


def test_dashboard_metric_uses_latest_valid_blood_pressure_pair():
    first_timestamp = "2026-05-01T08:00:00+00:00"
    invalid_timestamp = "2026-05-01T09:00:00+00:00"
    systolic_payload = {
        "value": 122.0,
        "unit": "mmHg",
        "status": "ready",
        "source": "google_fit",
        "last_updated": invalid_timestamp,
        "series": [
            {"timestamp": first_timestamp, "value": 120.0},
            {"timestamp": invalid_timestamp, "value": 122.0},
        ],
    }
    diastolic_payload = {
        "value": 122.0,
        "unit": "mmHg",
        "status": "ready",
        "source": "google_fit",
        "last_updated": invalid_timestamp,
        "series": [
            {"timestamp": first_timestamp, "value": 80.0},
            {"timestamp": invalid_timestamp, "value": 122.0},
        ],
    }

    metric = _build_blood_pressure_metric(
        systolic_payload,
        diastolic_payload,
        user_id="user-1",
    )

    assert metric["status"] == "ready"
    assert metric["value"] == {"systolic": 120.0, "diastolic": 80.0}
    assert metric["last_updated"] == first_timestamp
    assert metric["series"] == [
        {"timestamp": first_timestamp, "systolic": 120.0, "diastolic": 80.0}
    ]


def test_dashboard_metric_marks_duplicate_blood_pressure_as_missing():
    timestamp = "2026-05-01T09:00:00+00:00"
    systolic_payload = {
        "value": 122.0,
        "unit": "mmHg",
        "status": "ready",
        "source": "google_fit",
        "last_updated": timestamp,
        "series": [{"timestamp": timestamp, "value": 122.0}],
    }
    diastolic_payload = {
        "value": 122.0,
        "unit": "mmHg",
        "status": "ready",
        "source": "google_fit",
        "last_updated": timestamp,
        "series": [{"timestamp": timestamp, "value": 122.0}],
    }

    metric = _build_blood_pressure_metric(
        systolic_payload,
        diastolic_payload,
        user_id="user-1",
    )

    assert metric["status"] == "missing"
    assert metric["value"] is None
    assert metric["systolic"] is None
    assert metric["diastolic"] is None


def test_dashboard_metric_returns_partial_blood_pressure_when_diastolic_missing():
    systolic_timestamp = "2026-05-01T09:00:00+00:00"
    systolic_payload = {
        "value": 120.0,
        "unit": "mmHg",
        "status": "ready",
        "source": "google_fit",
        "last_updated": systolic_timestamp,
        "series": [{"timestamp": systolic_timestamp, "value": 120.0}],
    }
    diastolic_payload = {
        "value": None,
        "unit": "mmHg",
        "status": "no_data",
        "source": "google_fit",
        "last_updated": None,
        "series": [],
    }

    metric = _build_blood_pressure_metric(
        systolic_payload,
        diastolic_payload,
        user_id="user-1",
    )

    assert metric["status"] == "partial"
    assert metric["value"] == {"systolic": 120.0, "diastolic": None}
    assert metric["systolic"] == 120.0
    assert metric["diastolic"] is None


def test_dashboard_glucose_metric_uses_source_unit_for_display_and_consistent_series():
    now = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(
            value=85.0,
            unit="mg/dL",
            raw_value=85.0,
            raw_unit="mg/dL",
            normalized_value=85.0,
            normalized_unit="mg/dL",
            timestamp=now - timedelta(hours=2),
            source=UserVitalSourceEnum.GOOGLE_FIT,
        ),
        SimpleNamespace(
            value=81.0,
            unit="mg/dL",
            raw_value=4.5,
            raw_unit="mmol/L",
            normalized_value=81.0,
            normalized_unit="mg/dL",
            timestamp=now - timedelta(hours=1),
            source=UserVitalSourceEnum.GOOGLE_FIT,
        ),
    ]

    with patch("services.dashboard_service._query_vital_rows", return_value=rows):
        payload = _build_glucose_metric_payload(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["raw_value"] == 4.5
    assert payload["raw_unit"] == "mmol/L"
    assert payload["normalized_value"] == 81.0
    assert payload["normalized_unit"] == "mg/dL"
    assert payload["display_value"] == 4.5
    assert payload["display_unit"] == "mmol/L"
    assert payload["unit"] == "mmol/L"
    assert payload["precision"] == 1
    assert [point["value"] for point in payload["series"]] == [4.7, 4.5]
    assert all(point["unit"] == "mmol/L" for point in payload["series"])
