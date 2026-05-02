from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "data" / "llm_dataset" / "clinical_conversations.jsonl"

REQUIRED_KEYS = ("instruction", "input", "output")
FOLLOW_UP_PATTERNS = (
    "?",
    "i would ask",
    "important questions",
    "clinicians will ask",
    "follow-up details",
    "key questions",
    "need to know",
    "note the exact",
    "note temperature",
)
SAFETY_PATTERNS = (
    "not a diagnosis",
    "cannot diagnose",
    "guidance, not a diagnosis",
    "seek urgent care",
    "seek immediate medical care",
    "urgent medical",
)
CRITICAL_PATTERNS = (
    "chest pressure",
    "face droop",
    "trouble speaking",
    "one-sided weakness",
    "oxygen saturation 89",
    "throat tightness",
    "wheezing",
    "severe headache",
    "neck stiffness",
    "bp 184",
    "blurred vision",
)
FORBIDDEN_DIAGNOSIS_PATTERNS = (
    r"\byou have (?:a |an )?(?:heart attack|stroke|diabetes|appendicitis|meningitis|blood clot|anemia)\b",
    r"\bthe diagnosis is\b",
    r"\bthis is definitely\b",
    r"\bguaranteed\b",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_number}: expected JSON object")
            payload["_line_number"] = line_number
            rows.append(payload)
    return rows


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _has_critical_presentation(text: str) -> bool:
    lowered = text.lower()
    for pattern in CRITICAL_PATTERNS:
        start = lowered.find(pattern)
        while start != -1:
            prefix = lowered[max(0, start - 12) : start]
            if not prefix.endswith(("no ", "no new ", "without ")):
                return True
            start = lowered.find(pattern, start + len(pattern))
    return False


def validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["dataset is empty"]

    for row in rows:
        line_number = row.get("_line_number", "?")
        for key in REQUIRED_KEYS:
            value = row.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"line {line_number}: missing non-empty string key '{key}'")

        instruction = str(row.get("instruction") or "")
        input_text = str(row.get("input") or "")
        output = str(row.get("output") or "")
        combined_input = f"{instruction} {input_text}".lower()
        lowered_output = output.lower()

        if not _contains_any(lowered_output, FOLLOW_UP_PATTERNS):
            errors.append(f"line {line_number}: output should include at least one follow-up question or question cue")
        if not _contains_any(lowered_output, SAFETY_PATTERNS):
            errors.append(f"line {line_number}: output should include diagnosis limitation or safety guidance")
        if _has_critical_presentation(combined_input) and "seek immediate medical care" not in lowered_output:
            errors.append(f"line {line_number}: critical presentation must include 'Seek immediate medical care'")

        for pattern in FORBIDDEN_DIAGNOSIS_PATTERNS:
            if re.search(pattern, lowered_output):
                errors.append(f"line {line_number}: unsafe definitive diagnosis phrase matched '{pattern}'")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ArogyaAI clinical LoRA JSONL data.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = _read_jsonl(args.dataset)
    errors = validate_rows(rows)
    if errors:
        print(f"Dataset validation failed for {args.dataset}:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Dataset validation passed: {len(rows)} rows at {args.dataset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
