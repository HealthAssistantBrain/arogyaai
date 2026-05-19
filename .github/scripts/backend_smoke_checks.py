#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
for candidate in (REPO_ROOT, BACKEND_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)


def require_env(keys: list[str]) -> None:
    for key in keys:
        value = os.getenv(key, "")
        if not value or "your_" in value.lower():
            fail(f"Backend runtime env is missing or unsafe: {key}")


def import_required(module_name: str) -> object:
    started = time.perf_counter()
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        fail(f"Failed to import {module_name}: {exc}")
    print(f"[BACKEND] Imported {module_name} in {(time.perf_counter() - started) * 1000:.1f}ms")
    return module


def main() -> int:
    require_env(
        [
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET_KEY",
            "APP_ENCRYPTION_KEY",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "SUPABASE_SERVICE_ROLE_KEY",
        ]
    )

    main_module = import_required("main")
    app = getattr(main_module, "app", None)
    if app is None:
        fail("FastAPI app is not exported from main.py")

    route_paths = {getattr(route, "path", "") for route in app.routes}
    for path in ("/health", "/api/v1/health", "/ws/dashboard/{user_id}"):
        if path not in route_paths:
            fail(f"Backend route is missing: {path}")

    import_required("core.celery_app")
    import_required("ai.providers.runtime.provider_runtime")
    import_required("ai.scoring.core.scoring_engine")
    import_required("services.recommendation_engine")
    import_required("services.health_service")

    for config in ("alembic.ini", "alembic_analytics.ini"):
        if not (BACKEND_ROOT / config).exists():
            fail(f"Migration config missing: {config}")

    print("[BACKEND] Startup import, route, worker, scoring, recommendation, and migration contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
