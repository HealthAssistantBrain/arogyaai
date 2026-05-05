from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo
import asyncio
import sys

from fastapi import HTTPException
import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from core.config import settings  # noqa: E402
from pipelines.ingestion_pipeline.service import compute_daily_step_summary, compute_daily_steps  # noqa: E402
import services.google_fit_service as google_fit_service_module  # noqa: E402
from services.google_fit_service import (  # noqa: E402
    BloodPressureFetchResult,
    GOOGLE_FIT_ACTIVITY_SCOPE,
    GOOGLE_FIT_BODY_SCOPE,
    GOOGLE_FIT_BLOOD_GLUCOSE_SCOPE,
    GOOGLE_FIT_BLOOD_PRESSURE_SCOPE,
    GOOGLE_FIT_BODY_TEMPERATURE_SCOPE,
    GOOGLE_FIT_DAILY_BUCKET_MILLIS,
    GOOGLE_FIT_DATASOURCE_ID,
    GOOGLE_FIT_LOCATION_SCOPE,
    GOOGLE_FIT_OXYGEN_SCOPE,
    GOOGLE_FIT_SLEEP_SCOPE,
    GOOGLE_FIT_STEP_DATA_TYPE,
    GoogleFitService,
)


def test_google_fit_verify_uses_explicit_ca_bundle(monkeypatch):
    ca_bundle = Path(__file__).resolve()
    monkeypatch.setattr(settings, "GOOGLE_FIT_SSL_VERIFY", True)
    monkeypatch.setattr(settings, "GOOGLE_FIT_CA_BUNDLE", str(ca_bundle))
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    assert GoogleFitService._google_fit_verify() == str(ca_bundle)


def test_google_fit_verify_allows_dev_only_disable(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_FIT_SSL_VERIFY", False)
    monkeypatch.setattr(settings, "APP_ENV", "development")

    assert GoogleFitService._google_fit_verify() is False


def test_google_fit_verify_ignores_disable_outside_dev(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_FIT_SSL_VERIFY", False)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "GOOGLE_FIT_CA_BUNDLE", "")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    assert GoogleFitService._google_fit_verify()


def test_scope_status_accepts_required_google_fit_scopes():
    connection = SimpleNamespace(
        scopes=" ".join(
            [
                GOOGLE_FIT_ACTIVITY_SCOPE,
                GOOGLE_FIT_BODY_SCOPE,
                GOOGLE_FIT_SLEEP_SCOPE,
                GOOGLE_FIT_OXYGEN_SCOPE,
                GOOGLE_FIT_BLOOD_GLUCOSE_SCOPE,
                GOOGLE_FIT_BLOOD_PRESSURE_SCOPE,
                GOOGLE_FIT_BODY_TEMPERATURE_SCOPE,
                GOOGLE_FIT_LOCATION_SCOPE,
            ]
        )
    )

    assert GoogleFitService._scope_status(connection) == {
        "steps": True,
        "heart_rate": True,
        "sleep": True,
        "spo2": True,
        "glucose": True,
        "blood_pressure": True,
        "body_temperature": True,
        "location": True,
    }


def test_fetch_steps_uses_estimated_step_source_only():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"intVal": 3210}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_steps(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == GOOGLE_FIT_STEP_DATA_TYPE
    assert aggregate.await_args.args[4] == GOOGLE_FIT_DAILY_BUCKET_MILLIS
    assert aggregate.await_args.kwargs["data_source_id"] == GOOGLE_FIT_DATASOURCE_ID
    assert aggregate.await_args.kwargs["bucket_period"] == {"type": "day", "value": 1, "timeZoneId": "UTC"}
    assert records[0]["type"] == "steps"
    assert records[0]["value"] == 3210
    assert records[0]["source_used"] == GOOGLE_FIT_DATASOURCE_ID


def test_filter_data_sources_by_metric():
    sources = [
        {"dataStreamId": "heart-source", "dataType": {"name": "com.google.heart_rate.bpm"}},
        {"dataStreamId": GOOGLE_FIT_DATASOURCE_ID, "dataType": {"name": "com.google.step_count.delta"}},
        {"dataStreamId": "raw:com.google.step_count.delta:device_vendor:step-source", "dataType": {"name": "com.google.step_count.delta"}},
        {"dataStreamId": "sleep-source", "dataType": {"name": "com.google.sleep.segment"}},
        {"dataStreamId": "spo2-source", "dataType": {"name": "com.google.oxygen_saturation"}},
        {"dataStreamId": "glucose-source", "dataType": {"name": "com.google.blood_glucose"}},
        {"dataStreamId": "bp-source", "dataType": {"name": "com.google.blood_pressure"}},
        {"dataStreamId": "temperature-source", "dataType": {"name": "com.google.body.temperature"}},
        {"dataStreamId": "location-source", "dataType": {"name": "com.google.location.sample"}},
        {"dataStreamId": "ignored-source", "dataType": {"name": "com.google.weight"}},
    ]

    filtered = GoogleFitService._filter_data_sources_by_metric(sources)

    assert [source["dataStreamId"] for source in filtered["heart_rate"]] == ["heart-source"]
    assert [source["dataStreamId"] for source in filtered["steps"]] == [
        GOOGLE_FIT_DATASOURCE_ID,
        "raw:com.google.step_count.delta:device_vendor:step-source",
    ]
    assert [source["dataStreamId"] for source in filtered["sleep"]] == ["sleep-source"]
    assert [source["dataStreamId"] for source in filtered["spo2"]] == ["spo2-source"]
    assert [source["dataStreamId"] for source in filtered["glucose"]] == ["glucose-source"]
    assert [source["dataStreamId"] for source in filtered["blood_pressure"]] == ["bp-source"]
    assert [source["dataStreamId"] for source in filtered["body_temperature"]] == ["temperature-source"]
    assert [source["dataStreamId"] for source in filtered["location"]] == ["location-source"]


def test_aggregate_fit_data_sends_step_data_type_with_estimated_source():
    response = SimpleNamespace(
        status_code=200,
        is_error=False,
        text='{"bucket":[]}',
        json=lambda: {"bucket": []},
    )

    with patch.object(GoogleFitService, "_google_api_request", new=AsyncMock(return_value=response)) as request:
        asyncio.run(
            GoogleFitService._aggregate_fit_data(
                "token",
                GOOGLE_FIT_STEP_DATA_TYPE,
                1_777_500_000_000,
                1_777_586_400_000,
                GOOGLE_FIT_DAILY_BUCKET_MILLIS,
                data_source_id=GOOGLE_FIT_DATASOURCE_ID,
            )
        )

    request.assert_awaited_once()
    body = request.await_args.kwargs["json"]
    assert body["aggregateBy"] == [
        {
            "dataTypeName": GOOGLE_FIT_STEP_DATA_TYPE,
            "dataSourceId": GOOGLE_FIT_DATASOURCE_ID,
        }
    ]
    assert body["bucketByTime"] == {"durationMillis": GOOGLE_FIT_DAILY_BUCKET_MILLIS}


def test_aggregate_fit_data_can_bucket_steps_by_local_day_period():
    response = SimpleNamespace(
        status_code=200,
        is_error=False,
        text='{"bucket":[]}',
        json=lambda: {"bucket": []},
    )

    with patch.object(GoogleFitService, "_google_api_request", new=AsyncMock(return_value=response)) as request:
        asyncio.run(
            GoogleFitService._aggregate_fit_data(
                "token",
                GOOGLE_FIT_STEP_DATA_TYPE,
                1_777_500_000_000,
                1_777_586_400_000,
                GOOGLE_FIT_DAILY_BUCKET_MILLIS,
                data_source_id=GOOGLE_FIT_DATASOURCE_ID,
                bucket_period={"type": "day", "value": 1, "timeZoneId": "Asia/Kolkata"},
            )
        )

    body = request.await_args.kwargs["json"]
    assert body["bucketByTime"] == {
        "period": {"type": "day", "value": 1, "timeZoneId": "Asia/Kolkata"}
    }


def test_google_api_request_retries_once_after_timeout(monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        is_error=False,
        text='{"bucket":[]}',
        json=lambda: {"bucket": []},
    )
    attempts = {"count": 0}

    class FakeAsyncClient:
        def __init__(self, *, timeout, verify):
            assert timeout == 12.0
            self.verify = verify

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise httpx.ReadTimeout("timed out")
            return response

    sleep_mock = AsyncMock()
    monkeypatch.setattr(google_fit_service_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(google_fit_service_module.asyncio, "sleep", sleep_mock)

    result = asyncio.run(
        GoogleFitService._google_api_request(
            "GET",
            "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
            operation="aggregate:test",
            timeout=12.0,
        )
    )

    assert result is response
    assert attempts["count"] == 2
    sleep_mock.assert_awaited_once_with(1.0)


def test_fetch_steps_ignores_duplicate_step_sources_and_uses_estimated_source():
    first_start = int(datetime(2026, 4, 29, tzinfo=timezone.utc).timestamp() * 1000)
    second_start = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    first_response = {
        "bucket": [
            {
                "startTimeMillis": str(first_start),
                "dataset": [{"point": [{"value": [{"intVal": 1200}]}]}],
            }
        ]
    }
    second_response = {
        "bucket": [
            {
                "startTimeMillis": str(second_start),
                "dataset": [{"point": [{"value": [{"intVal": 3400}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(side_effect=[second_response, first_response])) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_steps(
                SimpleNamespace(id="user-1"),
                "token",
                days=2,
                timezone_name="UTC",
                start_ts=first_start,
                end_ts=end_millis,
                data_sources=[
                    {"dataStreamId": "raw:com.google.step_count.delta:device_vendor:step-source-1", "dataType": {"name": "com.google.step_count.delta"}},
                    {"dataStreamId": GOOGLE_FIT_DATASOURCE_ID, "dataType": {"name": "com.google.step_count.delta"}},
                    {"dataStreamId": "raw:com.google.step_count.delta:device_vendor:step-source-2", "dataType": {"name": "com.google.step_count.delta"}},
                ],
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.kwargs["data_source_id"] == GOOGLE_FIT_DATASOURCE_ID
    assert aggregate.await_args.kwargs["bucket_period"] == {"type": "day", "value": 1, "timeZoneId": "UTC"}
    assert [record["local_day"] for record in records] == ["2026-04-29", "2026-04-30"]
    assert [record["value"] for record in records] == [0, 3400]


def test_fetch_steps_does_not_use_raw_dataset_fallback_for_empty_estimated_aggregate():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)

    with (
        patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value={"bucket": []})) as aggregate,
        patch.object(GoogleFitService, "_fetch_raw_dataset", new=AsyncMock(return_value={"point": []})) as raw_dataset,
    ):
        records = asyncio.run(
            GoogleFitService.fetch_steps(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
                data_sources=[
                    {
                        "dataStreamId": "third-party-step-source",
                        "dataType": {"name": "com.google.step_count.delta"},
                    }
                ],
            )
        )

    aggregate.assert_awaited_once()
    raw_dataset.assert_not_awaited()
    assert records == []


def test_fetch_heart_rate_uses_first_prioritized_non_zero_source():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    first_response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 80.0}]}]}],
            }
        ]
    }
    second_response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 100.0}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(side_effect=[second_response, first_response])) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_heart_rate(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
                data_sources=[
                    {"dataStreamId": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm", "dataType": {"name": "com.google.heart_rate.bpm"}},
                    {"dataStreamId": "raw:com.google.heart_rate.bpm:device_vendor:heart-source-2", "dataType": {"name": "com.google.heart_rate.bpm"}},
                ],
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.kwargs["data_source_id"] == "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
    assert records[0]["type"] == "heart_rate"
    assert records[0]["value"] == 100.0


def test_fetch_sleep_reads_sleep_segments_as_hours():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "endTimeMillis": str(end_millis),
                "dataset": [
                    {
                        "point": [
                            {
                                "startTimeNanos": str(start_millis * 1_000_000),
                                "endTimeNanos": str(start_millis * 1_000_000 + 7_200_000_000_000),
                                "value": [{"intVal": 2}],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_sleep(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.sleep.segment"
    assert records[0]["type"] == "sleep"
    assert records[0]["unit"] == "hours"
    assert records[0]["value"] == 2.0


def test_fetch_spo2_reads_oxygen_saturation():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 97.5}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_spo2(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.oxygen_saturation"
    assert records[0]["type"] == "spo2"
    assert records[0]["unit"] == "%"
    assert records[0]["value"] == 97.5


def test_fetch_spo2_ignores_summary_aggregate_client_error_after_empty_primary():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)

    with patch.object(
        GoogleFitService,
        "_aggregate_fit_data",
        new=AsyncMock(
            side_effect=[
                {"bucket": []},
                HTTPException(status_code=400, detail="Failed to fetch Google Fit data for com.google.oxygen_saturation.summary"),
            ]
        ),
    ) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_spo2(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert records == []
    assert aggregate.await_count == 2
    assert aggregate.await_args_list[1].args[1] == "com.google.oxygen_saturation.summary"


def test_fetch_glucose_normalizes_google_fit_mmol_to_mg_dl():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 5.8}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_glucose(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.blood_glucose"
    assert records[0]["type"] == "glucose"
    assert records[0]["unit"] == "mg/dL"
    assert records[0]["value"] == 104.5


def test_fetch_blood_pressure_splits_systolic_and_diastolic_records():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 122.0}, {"fpVal": 78.0}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.blood_pressure"
    assert [record["type"] for record in records] == [
        "blood_pressure",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
    ]
    assert records[0]["metadata"] == {"systolic": 122.0, "diastolic": 78.0}
    assert records[1]["value"] == 122.0
    assert records[2]["value"] == 78.0


def test_fetch_blood_pressure_ignores_summary_aggregate_client_error_after_empty_primary():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)

    with patch.object(
        GoogleFitService,
        "_aggregate_fit_data",
        new=AsyncMock(
            side_effect=[
                {"bucket": []},
                HTTPException(status_code=400, detail="Failed to fetch Google Fit data for com.google.blood_pressure.summary"),
            ]
        ),
    ) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert records == []
    assert aggregate.await_count == 2
    assert aggregate.await_args_list[1].args[1] == "com.google.blood_pressure.summary"


def test_fetch_blood_pressure_uses_source_raw_fallback_for_manual_entries():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 128.0}, {"fpVal": 82.0}]}]}],
            }
        ]
    }

    with (
        patch.object(GoogleFitService, "_fetch_source_dataset_with_raw_fallback", new=AsyncMock(return_value=response)) as source_fetch,
        patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value={"bucket": []})) as aggregate,
    ):
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
                data_sources=[
                    {
                        "dataStreamId": "raw:com.google.blood_pressure:com.google.android.apps.fitness:user_input",
                        "dataType": {"name": "com.google.blood_pressure"},
                    }
                ],
            )
        )

    source_fetch.assert_awaited_once()
    aggregate.assert_not_awaited()
    assert [record["type"] for record in records] == [
        "blood_pressure",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
    ]
    assert records[0]["metadata"] == {"systolic": 128.0, "diastolic": 82.0}
    assert records[1]["value"] == 128.0
    assert records[2]["value"] == 82.0


def test_fetch_blood_pressure_keeps_130_over_85_distinct():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 130.0}, {"fpVal": 85.0}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)):
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert records[0]["metadata"] == {"systolic": 130.0, "diastolic": 85.0}
    assert records[1]["type"] == "blood_pressure_systolic"
    assert records[1]["value"] == 130.0
    assert records[2]["type"] == "blood_pressure_diastolic"
    assert records[2]["value"] == 85.0


def test_parse_blood_pressure_reads_summary_map_values():
    assert GoogleFitService.parse_blood_pressure(
        {
            "value": [
                {
                    "mapVal": {
                        "systolic": {"fpVal": 120.0},
                        "diastolic": {"fpVal": 80.0},
                    }
                }
            ]
        }
    ) == (120.0, 80.0)


def test_parse_blood_pressure_uses_median_for_mixed_aggregate_values():
    assert GoogleFitService.parse_blood_pressure(
        {
            "value": [
                {"fpVal": 121.0},
                {"fpVal": 125.0},
                {"fpVal": 126.0},
                {"fpVal": 78.0},
                {"fpVal": 80.0},
                {"fpVal": 85.0},
                {"intVal": 3},
                {"intVal": 1},
            ]
        }
    ) == (125.0, 80.0)


def test_fetch_blood_pressure_reads_summary_mapval_list_entries():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [
                    {
                        "point": [
                            {
                                "startTimeNanos": str(start_millis * 1_000_000),
                                "endTimeNanos": str(end_millis * 1_000_000),
                                "value": [
                                    {
                                        "mapVal": [
                                            {"key": "systolic", "value": {"fpVal": 121.0}},
                                            {"key": "diastolic", "value": {"fpVal": 80.0}},
                                        ]
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)):
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert [record["type"] for record in records] == [
        "blood_pressure",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
    ]
    assert records[0]["metadata"] == {"systolic": 121.0, "diastolic": 80.0}
    assert records[1]["value"] == 121.0
    assert records[2]["value"] == 80.0


def test_fetch_blood_pressure_uses_median_for_mixed_aggregate_values():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [
                    {
                        "point": [
                            {
                                "value": [
                                    {"fpVal": 121.0},
                                    {"fpVal": 125.0},
                                    {"fpVal": 126.0},
                                    {"fpVal": 78.0},
                                    {"fpVal": 80.0},
                                    {"fpVal": 85.0},
                                    {"intVal": 3},
                                    {"intVal": 1},
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)):
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert [record["type"] for record in records] == [
        "blood_pressure",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
    ]
    assert records[0]["metadata"] == {"systolic": 125.0, "diastolic": 80.0}
    assert records[1]["value"] == 125.0
    assert records[2]["value"] == 80.0


def test_parse_blood_pressure_rejects_duplicate_values():
    assert GoogleFitService.parse_blood_pressure(
        {"value": [{"fpVal": 122.0}, {"fpVal": 122.0}]}
    ) is None


def test_fetch_blood_pressure_skips_invalid_duplicate_values_from_raw_fallback():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 122.0}, {"fpVal": 122.0}]}]}],
            }
        ],
        "raw_dataset_size": 1,
    }

    with (
        patch.object(GoogleFitService, "_fetch_source_dataset_with_raw_fallback", new=AsyncMock(return_value=response)) as source_fetch,
        patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value={"bucket": []})) as aggregate,
    ):
        records = asyncio.run(
            GoogleFitService.fetch_blood_pressure(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
                data_sources=[
                    {
                        "dataStreamId": "raw:com.google.blood_pressure:com.google.android.apps.fitness:user_input",
                        "dataType": {"name": "com.google.blood_pressure"},
                    }
                ],
            )
        )

    source_fetch.assert_awaited_once()
    aggregate.assert_not_awaited()
    assert records == []


def test_sync_steps_overwrites_stale_blood_pressure_when_bp_fetch_is_empty():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 6, tzinfo=timezone.utc).timestamp() * 1000)
    connection = SimpleNamespace(
        default_timezone="UTC",
        last_synced_at=None,
        raw_last_response={},
        last_sync_status=None,
        google_email="user@example.com",
        device_id=None,
    )
    user = SimpleNamespace(id="user-1")
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    store_vitals_mock = MagicMock(return_value=[])

    all_scopes_ready = {
        "steps": True,
        "heart_rate": True,
        "sleep": True,
        "spo2": True,
        "glucose": True,
        "blood_pressure": True,
        "body_temperature": True,
        "location": True,
    }
    step_record = {
        "type": "steps",
        "value": 3210,
        "unit": "count",
        "timestamp": datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc),
        "source": "google_fit",
        "timezone": "UTC",
    }

    with ExitStack() as stack:
        stack.enter_context(patch.object(GoogleFitService, "validate_sync_auth", new=AsyncMock(return_value=(connection, "token", None))))
        stack.enter_context(patch.object(GoogleFitService, "_list_data_sources", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "_filter_data_sources_by_metric", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_scope_status", return_value=all_scopes_ready))
        stack.enter_context(patch.object(GoogleFitService, "fetch_steps", new=AsyncMock(return_value=[step_record])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_heart_rate", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_sleep", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_spo2", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_glucose", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_blood_pressure", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_body_temperature", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_location", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "_stored_step_totals_by_day", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_filter_delayed_step_records", return_value=([step_record], {})))
        stack.enter_context(patch.object(google_fit_service_module.UserDataService, "store_vitals", store_vitals_mock))
        stack.enter_context(patch.object(google_fit_service_module.UserDataService, "store_wearable_metrics", return_value=[]))
        stack.enter_context(patch.object(GoogleFitService, "_get_or_create_device", return_value=SimpleNamespace(id="device-1", is_active=False)))
        stack.enter_context(patch.object(GoogleFitService, "_data_availability_from_user_vitals", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_count_user_vitals_by_metric", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_step_debug_payload", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_connection_raw_payload", return_value={}))
        stack.enter_context(patch.object(google_fit_service_module, "generate_health_alerts"))
        stack.enter_context(patch.object(google_fit_service_module, "emit_event"))
        asyncio.run(
            GoogleFitService.sync_steps(
                db,
                user,
                timezone_name="UTC",
                days=6,
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    overwrite_types = store_vitals_mock.call_args.kwargs["overwrite_types"]
    assert "blood_pressure_systolic" in [value.value for value in overwrite_types]
    assert "blood_pressure_diastolic" in [value.value for value in overwrite_types]


def test_sync_steps_does_not_overwrite_blood_pressure_when_bp_fetch_is_invalid():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 6, tzinfo=timezone.utc).timestamp() * 1000)
    connection = SimpleNamespace(
        default_timezone="UTC",
        last_synced_at=None,
        raw_last_response={},
        last_sync_status=None,
        google_email="user@example.com",
        device_id=None,
    )
    user = SimpleNamespace(id="user-1")
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    store_vitals_mock = MagicMock(return_value=[])

    all_scopes_ready = {
        "steps": True,
        "heart_rate": True,
        "sleep": True,
        "spo2": True,
        "glucose": True,
        "blood_pressure": True,
        "body_temperature": True,
        "location": True,
    }
    step_record = {
        "type": "steps",
        "value": 3210,
        "unit": "count",
        "timestamp": datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc),
        "source": "google_fit",
        "timezone": "UTC",
    }

    with ExitStack() as stack:
        stack.enter_context(patch.object(GoogleFitService, "validate_sync_auth", new=AsyncMock(return_value=(connection, "token", None))))
        stack.enter_context(patch.object(GoogleFitService, "_list_data_sources", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "_filter_data_sources_by_metric", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_scope_status", return_value=all_scopes_ready))
        stack.enter_context(patch.object(GoogleFitService, "fetch_steps", new=AsyncMock(return_value=[step_record])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_heart_rate", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_sleep", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_spo2", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_glucose", new=AsyncMock(return_value=[])))
        stack.enter_context(
            patch.object(
                GoogleFitService,
                "fetch_blood_pressure",
                new=AsyncMock(return_value=BloodPressureFetchResult([], invalid_duplicate_detected=True)),
            )
        )
        stack.enter_context(patch.object(GoogleFitService, "fetch_body_temperature", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "fetch_location", new=AsyncMock(return_value=[])))
        stack.enter_context(patch.object(GoogleFitService, "_stored_step_totals_by_day", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_filter_delayed_step_records", return_value=([step_record], {})))
        stack.enter_context(patch.object(google_fit_service_module.UserDataService, "store_vitals", store_vitals_mock))
        stack.enter_context(patch.object(google_fit_service_module.UserDataService, "store_wearable_metrics", return_value=[]))
        stack.enter_context(patch.object(GoogleFitService, "_get_or_create_device", return_value=SimpleNamespace(id="device-1", is_active=False)))
        stack.enter_context(patch.object(GoogleFitService, "_data_availability_from_user_vitals", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_count_user_vitals_by_metric", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_step_debug_payload", return_value={}))
        stack.enter_context(patch.object(GoogleFitService, "_connection_raw_payload", return_value={}))
        stack.enter_context(patch.object(google_fit_service_module, "generate_health_alerts"))
        stack.enter_context(patch.object(google_fit_service_module, "emit_event"))
        asyncio.run(
            GoogleFitService.sync_steps(
                db,
                user,
                timezone_name="UTC",
                days=6,
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    overwrite_types = store_vitals_mock.call_args.kwargs["overwrite_types"]
    assert "blood_pressure_systolic" not in [value.value for value in overwrite_types]
    assert "blood_pressure_diastolic" not in [value.value for value in overwrite_types]


def test_fetch_body_temperature_reads_celsius():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 36.7}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_body_temperature(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.body.temperature"
    assert records[0]["type"] == "body_temperature"
    assert records[0]["unit"] == "celsius"
    assert records[0]["value"] == 36.7


def test_fetch_body_temperature_converts_fahrenheit_like_values_to_celsius():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 98.6}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)):
        records = asyncio.run(
            GoogleFitService.fetch_body_temperature(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert records[0]["type"] == "body_temperature"
    assert records[0]["unit"] == "celsius"
    assert records[0]["value"] == 37.0


def test_fetch_location_preserves_longitude_in_metadata():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "endTimeMillis": str(end_millis),
                "dataset": [{"point": [{"value": [{"fpVal": 12.97}, {"fpVal": 77.59}, {"fpVal": 8.0}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_location(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    aggregate.assert_awaited_once()
    assert aggregate.await_args.args[1] == "com.google.location.sample"
    assert records[0]["type"] == "location"
    assert records[0]["value"] == 12.97
    assert records[0]["metadata"]["longitude"] == 77.59
    assert records[0]["metadata"]["accuracy_meters"] == 8.0


def test_fetch_sleep_dedupes_overlapping_source_segments():
    start_millis = int(datetime(2026, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    source_response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "endTimeMillis": str(end_millis),
                "dataset": [
                    {
                        "point": [
                            {
                                "startTimeNanos": str(start_millis * 1_000_000),
                                "endTimeNanos": str(start_millis * 1_000_000 + 7_200_000_000_000),
                                "value": [{"intVal": 2}],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(side_effect=[source_response, source_response])) as aggregate:
        records = asyncio.run(
            GoogleFitService.fetch_sleep(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
                data_sources=[
                    {"dataStreamId": "sleep-source-1", "dataType": {"name": "com.google.sleep.segment"}},
                    {"dataStreamId": "sleep-source-2", "dataType": {"name": "com.google.sleep.segment"}},
                ],
            )
        )

    assert aggregate.await_count == 2
    assert [call.kwargs["data_source_id"] for call in aggregate.await_args_list] == ["sleep-source-1", "sleep-source-2"]
    assert records[0]["type"] == "sleep"
    assert records[0]["value"] == 2.0


def test_current_local_day_window_starts_at_midnight_in_user_timezone():
    local_day, start_millis, end_millis = GoogleFitService._build_current_local_day_window("Asia/Kolkata")
    tzinfo = ZoneInfo("Asia/Kolkata")
    start_local = datetime.fromtimestamp(start_millis / 1000, tz=timezone.utc).astimezone(tzinfo)
    end_local = datetime.fromtimestamp(end_millis / 1000, tz=timezone.utc).astimezone(tzinfo)

    assert local_day == end_local.date().isoformat()
    assert start_local.date() == end_local.date()
    assert (start_local.hour, start_local.minute, start_local.second, start_local.microsecond) == (0, 0, 0, 0)
    assert start_millis < end_millis


def test_paginated_fetch_windows_continue_to_previous_days_after_today():
    windows = GoogleFitService._build_paginated_fetch_windows("UTC", days=3, page_size_days=7)

    assert len(windows) == 3
    assert [window[3] for window in windows] == [1, 2, 3]
    assert [window_days for _start, _end, window_days, _page in windows] == [1, 1, 1]
    assert windows[1][1] == windows[0][0]
    assert windows[2][1] == windows[1][0]


def test_compute_daily_steps_buckets_by_local_date_descending():
    rows = [
        {"type": "steps", "value": 1200, "timestamp": "2026-04-30T20:30:00+00:00"},
        {"type": "steps", "value": 800, "timestamp": "2026-05-01T05:00:00+00:00"},
        {"type": "steps", "value": 500, "timestamp": "2026-04-29T18:00:00+00:00"},
    ]

    assert compute_daily_steps(rows, "Asia/Kolkata") == [
        {"date": "2026-05-01", "steps": 2000},
        {"date": "2026-04-29", "steps": 500},
    ]


def test_daily_step_summary_latest_day_is_most_recent_date_and_best_day_is_highest_steps():
    rows = [
        {"type": "steps", "value": 4120, "timestamp": "2026-04-29T18:30:00+00:00"},
        {"type": "steps", "value": 7739, "timestamp": "2026-04-30T18:30:00+00:00"},
        {"type": "steps", "value": 6093, "timestamp": "2026-05-01T18:30:00+00:00"},
    ]

    summary = compute_daily_step_summary(rows, "Asia/Kolkata")

    assert summary["daily_steps"] == [
        {"date": "2026-05-02", "steps": 6093},
        {"date": "2026-05-01", "steps": 7739},
        {"date": "2026-04-30", "steps": 4120},
    ]
    assert summary["latest_day"] == {"date": "2026-05-02", "steps": 6093}
    assert summary["best_day"] == {"date": "2026-05-01", "steps": 7739}


def test_build_stats_uses_canonical_daily_steps_for_totals_and_average():
    stats = GoogleFitService._build_stats(
        [
            {"date": "2026-04-30", "steps": 6850},
            {"date": "2026-05-01", "steps": 0},
        ]
    )

    assert stats["daily_steps"] == [
        {"date": "2026-05-01", "steps": 0},
        {"date": "2026-04-30", "steps": 6850},
    ]
    assert stats["latest_day"] == {"date": "2026-05-01", "steps": 0}
    assert stats["total_steps"] == 6850
    assert stats["average_steps"] == 3425
    assert stats["average_daily_steps"] == 3425
    assert stats["active_day_count"] == 1
    assert stats["valid_day_count"] == 2


def test_build_stats_includes_every_synced_day_in_rollups():
    stats = GoogleFitService._build_stats(
        [
            {"date": "2026-04-29", "steps": 5200, "is_partial": False},
            {"date": "2026-04-30", "steps": 6800, "is_partial": False},
            {"date": "2026-05-01", "steps": 2400, "is_partial": True},
        ],
        "UTC",
    )

    assert stats["latest_day"]["date"] == "2026-05-01"
    assert stats["latest_day"]["steps"] == 2400
    assert stats["latest_complete_day"] == stats["latest_day"]
    assert stats["total_steps"] == 14400
    assert stats["total_steps_including_partial"] == 14400
    assert stats["average_daily_steps"] == 4800
    assert stats["average_steps"] == 4800
    assert stats["best_day"]["date"] == "2026-04-30"
    assert stats["valid_day_count"] == 3
    assert stats["partial_day_count"] == 0


def test_build_stats_latest_day_uses_most_recent_date_not_best_complete_day():
    stats = GoogleFitService._build_stats(
        [
            {"date": "2026-04-30", "steps": 4120, "is_partial": False},
            {"date": "2026-05-01", "steps": 7739, "is_partial": False},
            {"date": "2026-05-02", "steps": 6093, "is_partial": True},
        ],
        "Asia/Kolkata",
    )

    assert stats["latest_day"] == {"date": "2026-05-02", "steps": 6093}
    assert stats["latest_complete_day"] == stats["latest_day"]
    assert stats["best_day"]["date"] == "2026-05-01"
    assert stats["best_day"]["steps"] == 7739
    assert stats["total_steps"] == 17952
    assert stats["total_steps_including_partial"] == 17952


def test_daily_payload_from_vital_rows_uses_canonical_local_date_buckets():
    start_millis = int(datetime(2026, 4, 29, 18, 30, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, 6, 30, tzinfo=timezone.utc).timestamp() * 1000)
    rows = [
        SimpleNamespace(timestamp=datetime(2026, 4, 29, 19, 0, tzinfo=timezone.utc), value=1200, vital_type="steps"),
        SimpleNamespace(timestamp=datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc), value=2300, vital_type="steps"),
        SimpleNamespace(timestamp=datetime(2026, 5, 1, 5, 0, tzinfo=timezone.utc), value=900, vital_type="steps"),
    ]

    payload = GoogleFitService._daily_payload_from_vital_rows(
        rows,
        "Asia/Kolkata",
        start_millis,
        end_millis,
    )

    assert payload == [
        {"date": "2026-05-01", "steps": 900},
        {"date": "2026-04-30", "steps": 3500},
    ]


def test_filter_delayed_step_records_keeps_last_known_higher_steps():
    timestamp = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    records = [
        {
            "type": "steps",
            "value": 0,
            "timestamp": timestamp,
            "source": "google_fit",
            "unit": "count",
        }
    ]

    filtered, delayed = GoogleFitService._filter_delayed_step_records(
        records,
        {"2026-05-01": 4000},
        timezone_name="UTC",
    )

    assert filtered == []
    assert delayed == {"2026-05-01": {"api_steps": 0, "stored_steps": 4000}}


def test_extract_step_count_dedupes_identical_timed_points():
    start_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    point = {
        "startTimeNanos": str((start_millis + 60_000) * 1_000_000),
        "endTimeNanos": str((start_millis + 120_000) * 1_000_000),
        "value": [{"intVal": 4127}],
    }

    assert GoogleFitService._extract_step_count({"dataset": [{"point": [point, dict(point)]}]}) == 4127


def test_fetch_steps_preserves_explicit_zero_from_google_fit():
    start_millis = int(datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_millis = int(datetime(2026, 5, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    response = {
        "bucket": [
            {
                "startTimeMillis": str(start_millis),
                "endTimeMillis": str(end_millis),
                "dataset": [{"point": [{"value": [{"intVal": 0}]}]}],
            }
        ]
    }

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value=response)):
        records = asyncio.run(
            GoogleFitService.fetch_steps(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=start_millis,
                end_ts=end_millis,
            )
        )

    assert records[0]["value"] == 0
    assert records[0]["raw_google_fit_steps"] == 0


def test_fetch_steps_propagates_ssl_transport_errors():
    ssl_error = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate in certificate chain")

    with patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(side_effect=ssl_error)):
        with pytest.raises(httpx.TransportError, match="CERTIFICATE_VERIFY_FAILED"):
            asyncio.run(
                GoogleFitService.fetch_steps(
                    SimpleNamespace(id="user-1"),
                    "token",
                    days=1,
                    timezone_name="UTC",
                    start_ts=1_777_500_000_000,
                    end_ts=1_777_586_400_000,
                )
            )


def test_empty_step_response_returns_no_zero_records():
    with (
        patch.object(GoogleFitService, "_aggregate_fit_data", new=AsyncMock(return_value={"bucket": []})),
        patch.object(GoogleFitService, "_fetch_raw_dataset", new=AsyncMock(return_value={"point": []})) as raw_dataset,
    ):
        records = asyncio.run(
            GoogleFitService.fetch_steps(
                SimpleNamespace(id="user-1"),
                "token",
                days=1,
                timezone_name="UTC",
                start_ts=1_777_500_000_000,
                end_ts=1_777_586_400_000,
            )
        )

    assert records == []
    raw_dataset.assert_not_awaited()
