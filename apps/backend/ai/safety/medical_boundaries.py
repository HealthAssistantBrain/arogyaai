from __future__ import annotations

import re

from .clinical_rules import FORBIDDEN_CERTAINTY_PATTERNS, MEDICATION_PATTERNS

_COMPILED_MED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in MEDICATION_PATTERNS]
_COMPILED_CERTAINTY_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in FORBIDDEN_CERTAINTY_PATTERNS
]


def check_medical_boundaries(text: str) -> tuple[bool, list[str]]:
    violations: list[str] = []
    for pattern in _COMPILED_MED_PATTERNS:
        if pattern.search(text or ""):
            violations.append(f"medication_pattern:{pattern.pattern[:60]}")
    return bool(violations), violations


def apply_certainty_softening(text: str) -> tuple[str, bool]:
    modified = text or ""
    changed = False
    for pattern, replacement in _COMPILED_CERTAINTY_PATTERNS:
        updated = pattern.sub(replacement, modified)
        if updated != modified:
            modified = updated
            changed = True
    return modified, changed


def strip_medication_instructions(text: str) -> tuple[str, bool]:
    modified = text or ""
    changed = False
    for pattern in _COMPILED_MED_PATTERNS:
        if pattern.search(modified):
            modified = pattern.sub(
                "[specific dosage or medication guidance removed. Please consult your doctor.]",
                modified,
            )
            changed = True
    return modified, changed
