from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services import supabase_sdk_validation as sdk_validation


def _locked_versions() -> dict[str, str]:
    return {
        "supabase": "2.6.0",
        "realtime": "1.0.6",
        "postgrest": "0.16.11",
        "storage3": "0.7.7",
        "gotrue": "2.12.4",
        "supafunc": "0.5.1",
        "httpx": "0.27.2",
    }


def _module_map() -> dict[str, object]:
    return {
        "supabase": SimpleNamespace(Client=object, create_client=lambda *_args, **_kwargs: object()),
        "realtime.connection": SimpleNamespace(Socket=object),
        "postgrest": SimpleNamespace(SyncPostgrestClient=object),
        "storage3": SimpleNamespace(SyncStorageClient=object),
        "gotrue": SimpleNamespace(SyncMemoryStorage=object),
    }


def test_validate_supabase_sdk_compatibility_accepts_locked_bundle(monkeypatch: pytest.MonkeyPatch):
    locked_versions = _locked_versions()
    modules = _module_map()

    monkeypatch.setattr(sdk_validation, "_read_locked_versions", lambda: locked_versions)
    monkeypatch.setattr(sdk_validation.metadata, "version", lambda package_name: locked_versions[package_name])
    monkeypatch.setattr(
        sdk_validation.metadata,
        "requires",
        lambda package_name: ["realtime (>=1.0.0,<2.0.0)"] if package_name == "supabase" else [],
    )
    monkeypatch.setattr(sdk_validation, "import_module", lambda module_name: modules[module_name])

    snapshot = sdk_validation.validate_supabase_sdk_compatibility(force=True, raise_on_error=False)

    assert snapshot["status"] == "healthy"
    assert snapshot["packages"]["realtime"] == "1.0.6"
    assert snapshot["imports"]["realtime.connection"] == "ok"


def test_validate_supabase_sdk_compatibility_rejects_realtime_drift(monkeypatch: pytest.MonkeyPatch):
    locked_versions = _locked_versions()
    installed_versions = {**locked_versions, "realtime": "2.0.0"}
    modules = _module_map()

    def _fake_import(module_name: str):
        if module_name == "realtime.connection":
            raise ModuleNotFoundError("No module named 'realtime.connection'")
        return modules[module_name]

    monkeypatch.setattr(sdk_validation, "_read_locked_versions", lambda: locked_versions)
    monkeypatch.setattr(sdk_validation.metadata, "version", lambda package_name: installed_versions[package_name])
    monkeypatch.setattr(sdk_validation.metadata, "requires", lambda _package_name: [])
    monkeypatch.setattr(sdk_validation, "import_module", _fake_import)

    with pytest.raises(sdk_validation.SupabaseSDKCompatibilityError) as exc_info:
        sdk_validation.validate_supabase_sdk_compatibility(force=True, raise_on_error=True)

    snapshot = exc_info.value.snapshot
    assert snapshot["status"] == "failed"
    assert any("version_mismatch:realtime" in error for error in snapshot["errors"])
    assert any("import_failure:realtime.connection" in error for error in snapshot["errors"])
