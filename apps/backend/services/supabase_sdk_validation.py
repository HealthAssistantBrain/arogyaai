from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from importlib import import_module, metadata
from pathlib import Path
from typing import Any

logger = logging.getLogger("supabase_sdk_validation")

_DEFAULT_LOCKED_VERSIONS = {
    "supabase": "2.6.0",
    "realtime": "1.0.6",
    "postgrest": "0.16.11",
    "storage3": "0.7.7",
    "gotrue": "2.12.4",
    "supafunc": "0.5.1",
    "httpx": "0.27.2",
}

_REQUIRED_IMPORTS: dict[str, tuple[str, ...]] = {
    "supabase": ("Client", "create_client"),
    "realtime.connection": ("Socket",),
    "postgrest": ("SyncPostgrestClient",),
    "storage3": ("SyncStorageClient",),
    "gotrue": ("SyncMemoryStorage",),
}

_LOCKFILE_PATH = Path(__file__).resolve().parents[1] / "supabase-sdk.lock.txt"
_RUNTIME_SYMBOL_CACHE: dict[str, Any] = {}
_LAST_VALIDATION_SNAPSHOT: dict[str, Any] = {
    "status": "unknown",
    "detail": "not_checked",
    "checked_at": None,
    "locked_versions": dict(_DEFAULT_LOCKED_VERSIONS),
    "packages": {},
    "imports": {},
    "supabase_requires": [],
    "errors": [],
    "warnings": [],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_locked_versions() -> dict[str, str]:
    if not _LOCKFILE_PATH.exists():
        return dict(_DEFAULT_LOCKED_VERSIONS)

    locked_versions: dict[str, str] = {}
    for raw_line in _LOCKFILE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        package_name, version = line.split("==", 1)
        locked_versions[package_name.strip()] = version.strip()

    return locked_versions or dict(_DEFAULT_LOCKED_VERSIONS)


def _store_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    global _LAST_VALIDATION_SNAPSHOT
    _LAST_VALIDATION_SNAPSHOT = copy.deepcopy(snapshot)
    return copy.deepcopy(snapshot)


class SupabaseSDKCompatibilityError(RuntimeError):
    def __init__(self, snapshot: dict[str, Any]):
        self.snapshot = copy.deepcopy(snapshot)
        error_text = "; ".join(snapshot.get("errors") or []) or "unknown_compatibility_error"
        super().__init__(
            "Supabase SDK compatibility validation failed. "
            f"{error_text}. Rebuild the backend image with the pinned SDK lockfile."
        )


def validate_supabase_sdk_compatibility(
    *,
    force: bool = False,
    raise_on_error: bool = True,
) -> dict[str, Any]:
    global _RUNTIME_SYMBOL_CACHE

    if not force and _LAST_VALIDATION_SNAPSHOT.get("status") == "healthy":
        return copy.deepcopy(_LAST_VALIDATION_SNAPSHOT)

    locked_versions = _read_locked_versions()
    snapshot: dict[str, Any] = {
        "status": "healthy",
        "detail": "supabase_sdk_locked",
        "checked_at": _utc_now(),
        "locked_versions": locked_versions,
        "packages": {},
        "imports": {},
        "supabase_requires": [],
        "errors": [],
        "warnings": [],
    }

    logger.info("[DEPENDENCY VALIDATION] Starting Supabase SDK compatibility check")

    for package_name, expected_version in locked_versions.items():
        try:
            installed_version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            snapshot["errors"].append(
                f"missing_package:{package_name} expected={expected_version}"
            )
            continue

        snapshot["packages"][package_name] = installed_version
        if installed_version != expected_version:
            snapshot["errors"].append(
                f"version_mismatch:{package_name} expected={expected_version} installed={installed_version}"
            )

    try:
        snapshot["supabase_requires"] = list(metadata.requires("supabase") or [])
    except metadata.PackageNotFoundError:
        snapshot["supabase_requires"] = []

    for module_name, required_attrs in _REQUIRED_IMPORTS.items():
        try:
            module = import_module(module_name)
        except Exception as exc:
            snapshot["imports"][module_name] = f"error:{exc.__class__.__name__}:{exc}"
            snapshot["errors"].append(f"import_failure:{module_name} error={exc}")
            continue

        missing_attrs = [attr_name for attr_name in required_attrs if not hasattr(module, attr_name)]
        if missing_attrs:
            snapshot["imports"][module_name] = f"missing_attrs:{','.join(missing_attrs)}"
            snapshot["errors"].append(
                f"missing_symbols:{module_name} attrs={','.join(missing_attrs)}"
            )
            continue

        snapshot["imports"][module_name] = "ok"

    realtime_version = snapshot["packages"].get("realtime")
    if realtime_version and realtime_version != locked_versions.get("realtime"):
        snapshot["warnings"].append(
            "realtime.connection is only guaranteed in the locked realtime 1.x family."
        )

    if snapshot["errors"]:
        snapshot["status"] = "failed"
        snapshot["detail"] = "supabase_sdk_incompatible"
        _RUNTIME_SYMBOL_CACHE = {}
        logger.error(
            "[PACKAGE COMPATIBILITY] Supabase SDK validation failed | packages=%s errors=%s",
            snapshot["packages"],
            snapshot["errors"],
        )
        logger.error(
            "[SUPABASE SDK] Declared requirements from installed supabase | requires=%s",
            snapshot["supabase_requires"],
        )
        stored_snapshot = _store_snapshot(snapshot)
        if raise_on_error:
            raise SupabaseSDKCompatibilityError(stored_snapshot)
        return stored_snapshot

    logger.info(
        "[SUPABASE SDK] Compatible locked SDK detected | packages=%s",
        snapshot["packages"],
    )
    logger.info(
        "[REALTIME SDK] realtime.connection import path verified | status=%s",
        snapshot["imports"].get("realtime.connection"),
    )
    return _store_snapshot(snapshot)


def ensure_supabase_sdk_compatibility(*, force: bool = False) -> dict[str, Any]:
    return validate_supabase_sdk_compatibility(force=force, raise_on_error=True)


def get_supabase_sdk_validation_snapshot() -> dict[str, Any]:
    if _LAST_VALIDATION_SNAPSHOT.get("checked_at") is None:
        return validate_supabase_sdk_compatibility(raise_on_error=False)
    return copy.deepcopy(_LAST_VALIDATION_SNAPSHOT)


def load_supabase_client_symbols() -> tuple[Any, Any]:
    ensure_supabase_sdk_compatibility()
    if "Client" in _RUNTIME_SYMBOL_CACHE and "create_client" in _RUNTIME_SYMBOL_CACHE:
        return _RUNTIME_SYMBOL_CACHE["Client"], _RUNTIME_SYMBOL_CACHE["create_client"]

    module = import_module("supabase")
    _RUNTIME_SYMBOL_CACHE["Client"] = getattr(module, "Client")
    _RUNTIME_SYMBOL_CACHE["create_client"] = getattr(module, "create_client")
    return _RUNTIME_SYMBOL_CACHE["Client"], _RUNTIME_SYMBOL_CACHE["create_client"]
