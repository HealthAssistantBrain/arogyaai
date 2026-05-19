#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


AREAS = {
    "frontend": ("apps/frontend/",),
    "backend": ("apps/backend/", "pipelines/",),
    "ai_runtime": (
        "apps/backend/ai/",
        "apps/backend/services/orchestrator/",
        "apps/backend/services/recommendation",
        "apps/backend/services/ollama_client.py",
        "apps/backend/tests/test_provider_runtime.py",
        "apps/backend/tests/test_ai_safety_validator.py",
        "apps/backend/tests/test_recommendation",
        "apps/backend/tests/test_health_scoring_engine.py",
        "pipelines/rag_pipeline/",
        "pipelines/ml_pipeline/",
    ),
    "infra": (
        "docker-compose.yml",
        ".dockerignore",
        "infra/",
        "apps/backend/Dockerfile",
        "apps/backend/docker/",
        "apps/frontend/Dockerfile",
        "pipelines/prediction-service/Dockerfile",
        "pipelines/rag-service/Dockerfile",
    ),
    "security": (
        ".github/workflows/security-scan.yml",
        ".github/env/",
        ".env.template",
        "apps/backend/.env.template",
        "apps/frontend/.env.template",
        "apps/backend/core/security.py",
        "apps/backend/core/auth.py",
        "apps/backend/services/supabase_jwt_verifier.py",
    ),
    "docs": ("docs/", "README.md"),
    "ci": (".github/",),
}


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def changed_files() -> list[str]:
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    before = os.getenv("GITHUB_EVENT_BEFORE", "")
    base_ref = os.getenv("GITHUB_BASE_REF", "")
    sha = os.getenv("GITHUB_SHA", "HEAD")

    candidates: list[list[str]] = []
    if event_name == "pull_request" and base_ref:
        candidates.append(["diff", "--name-only", f"origin/{base_ref}...{sha}"])
    if before and before != "0000000000000000000000000000000000000000":
        candidates.append(["diff", "--name-only", f"{before}...{sha}"])
    candidates.append(["diff", "--name-only", "HEAD~1...HEAD"])
    candidates.append(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])

    for args in candidates:
        try:
            output = run_git(args)
        except subprocess.CalledProcessError:
            continue
        files = sorted({line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()})
        if files:
            return files

    return []


def matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def emit(outputs: dict[str, object]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    lines = [f"{key}={value}" for key, value in outputs.items()]
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def main() -> int:
    files = changed_files()
    all_changed = not files
    flags = {
        area: all_changed or any(matches(path, prefixes) for path in files)
        for area, prefixes in AREAS.items()
    }
    code_changed = flags["frontend"] or flags["backend"] or flags["ai_runtime"] or flags["infra"]
    outputs: dict[str, object] = {
        **{key: str(value).lower() for key, value in flags.items()},
        "code": str(code_changed).lower(),
        "all": str(all_changed).lower(),
        "changed_files": json.dumps(files),
    }
    emit(outputs)
    print("[CI] Changed files:")
    print(json.dumps(files, indent=2))
    print("[CI] Area flags:")
    print(json.dumps(flags, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
