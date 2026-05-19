#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


SECRET_NAME_PATTERN = re.compile(
    r"(SECRET|PASSWORD|TOKEN|KEY|DATABASE_URL|SERVICE_ROLE|NVIDIA|OPENAI|SUPABASE)",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(r"(your_|example|change_me|placeholder)", re.IGNORECASE)
ALLOWED_TRACKED_ENV = {
    ".env.template",
    "apps/backend/.env.template",
    "apps/frontend/.env.template",
    ".github/env/backend.env.template",
    ".github/env/frontend.env.template",
    ".github/env/ci.env.template",
}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], text=True)
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def validate_templates(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.exists():
            errors.append(f"missing env template: {path}")
            continue
        values = parse_env(path)
        if not values:
            errors.append(f"empty env template: {path}")
        for key, value in values.items():
            if SECRET_NAME_PATTERN.search(key) and PLACEHOLDER_PATTERN.search(value):
                if path.as_posix().startswith(".github/env/"):
                    errors.append(f"{path}:{key} uses placeholder value in CI template")
    return errors


def validate_tracked_env_files() -> list[str]:
    errors: list[str] = []
    for path in tracked_files():
        name = Path(path).name
        if name.startswith(".env") and path not in ALLOWED_TRACKED_ENV:
            errors.append(f"tracked env file is not allowed: {path}")
    return errors


def validate_required_runtime_env(required: list[str]) -> list[str]:
    errors: list[str] = []
    for key in required:
        value = os.getenv(key, "")
        if not value:
            errors.append(f"missing required runtime env: {key}")
        elif PLACEHOLDER_PATTERN.search(value):
            errors.append(f"runtime env still uses placeholder value: {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ArogyaAI CI environment strategy.")
    parser.add_argument("--template", action="append", default=[], help="Env template to validate.")
    parser.add_argument("--require", action="append", default=[], help="Runtime env var that must be set.")
    args = parser.parse_args()

    errors = []
    errors.extend(validate_templates([Path(item) for item in args.template]))
    errors.extend(validate_tracked_env_files())
    errors.extend(validate_required_runtime_env(args.require))

    if errors:
        print("[SECURITY] Environment validation failed:")
        for error in errors:
            print(f"::error::{error}")
        return 1

    print("[SECURITY] Environment templates and tracked env files are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
