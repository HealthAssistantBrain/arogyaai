from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo
import asyncio
import sys

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from core.config import settings  # noqa: E402
from services.google_fit_service import (  # noqa: E402
    GOOGLE_FIT_ACTIVITY_SCOPE,
    GOOGLE_FIT_BODY_SCOPE,
    GOOGLE_FIT_DAILY_BUCKET_MILLIS,
    GOOGLE_FIT_DATASOURCE_ID,
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

    assert GoogleFitService._google_fit_verify() is False


def test_scope_status_accepts_required_google_fit_scopes():
    connection = SimpleNamespace(
        scopes=" ".join(
            [
                GOOGLE_FIT_ACTIVITY_SCOPE,
                GOOGLE_FIT_BODY_SCOPE,
                GOOGLE_FIT_SLEEP_SCOPE,
            ]
        )
    )

    assert GoogleFitService._scope_status(connection) == {
        "steps": True,
        "heart_rate": True,
        "sleep": True,
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
    assert records[0]["type"] == "steps"
    assert records[0]["value"] == 3210
    assert records[0]["source_used"] == GOOGLE_FIT_DATASOURCE_ID


def test_filter_data_sources_by_metric():
    sources = [
        {"dataStreamId": "heart-source", "dataType": {"name": "com.google.heart_rate.bpm"}},
        {"dataStreamId": GOOGLE_FIT_DATASOURCE_ID, "dataType": {"name": "com.google.step_count.delta"}},
        {"dataStreamId": "raw:com.google.step_count.delta:device_vendor:step-source", "dataType": {"name": "com.google.step_count.delta"}},
        {"dataStreamId": "sleep-source", "dataType": {"name": "com.google.sleep.segment"}},
        {"dataStreamId": "ignored-source", "dataType": {"name": "com.google.weight"}},
    ]

    filtered = GoogleFitService._filter_data_sources_by_metric(sources)

    assert [source["dataStreamId"] for source in filtered["heart_rate"]] == ["heart-source"]
    assert [source["dataStreamId"] for source in filtered["steps"]] == [
        GOOGLE_FIT_DATASOURCE_ID,
        "raw:com.google.step_count.delta:device_vendor:step-source",
    ]
    assert [source["dataStreamId"] for source in filtered["sleep"]] == ["sleep-source"]


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
    assert [record["value"] for record in records] == [3400]


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


def test_build_stats_uses_latest_active_day_for_latest_day():
    stats = GoogleFitService._build_stats(
        [
            {"date": "2026-04-30", "steps": 6850},
            {"date": "2026-05-01", "steps": 0},
        ]
    )

    assert stats["latest_day"] == {"date": "2026-04-30", "steps": 6850}
    assert stats["total_steps"] == 6850
    assert stats["active_day_count"] == 1


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
