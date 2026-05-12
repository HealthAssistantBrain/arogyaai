from __future__ import annotations

import sys
from importlib import import_module, metadata
from pathlib import Path

LOCKFILE = Path("/tmp/supabase-sdk.lock.txt")
REQUIRED_IMPORTS = {
    "supabase": ("Client", "create_client"),
    "realtime.connection": ("Socket",),
    "postgrest": ("SyncPostgrestClient",),
    "storage3": ("SyncStorageClient",),
    "gotrue": ("SyncMemoryStorage",),
}


def read_locked_versions() -> dict[str, str]:
    locked_versions: dict[str, str] = {}
    for raw_line in LOCKFILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        package_name, version = line.split("==", 1)
        locked_versions[package_name.strip()] = version.strip()
    return locked_versions


def main() -> int:
    locked_versions = read_locked_versions()
    errors: list[str] = []
    installed: dict[str, str] = {}

    print("[DEPENDENCY VALIDATION] validating locked Supabase SDK bundle")

    for package_name, expected_version in locked_versions.items():
        try:
            installed_version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            errors.append(f"missing_package:{package_name} expected={expected_version}")
            continue

        installed[package_name] = installed_version
        if installed_version != expected_version:
            errors.append(
                f"version_mismatch:{package_name} expected={expected_version} installed={installed_version}"
            )

    for module_name, attrs in REQUIRED_IMPORTS.items():
        try:
            module = import_module(module_name)
        except Exception as exc:
            errors.append(f"import_failure:{module_name} error={exc}")
            continue
        for attr_name in attrs:
            if not hasattr(module, attr_name):
                errors.append(f"missing_symbols:{module_name} attr={attr_name}")

    if errors:
        print(f"[PACKAGE COMPATIBILITY] failed | installed={installed} errors={errors}", file=sys.stderr)
        return 1

    print(f"[SUPABASE SDK] locked versions verified | installed={installed}")
    print("[REALTIME SDK] realtime.connection import path verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
