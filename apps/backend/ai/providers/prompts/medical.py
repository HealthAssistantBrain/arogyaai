from __future__ import annotations

import json
from typing import Any


def build_medical_json_prompt(*, task: str, instruction: str, context: dict[str, Any]) -> str:
    return (
        f"Task: {task}\n"
        "Return only compact, valid JSON.\n"
        "Use clinically cautious, patient-safe language. Do not diagnose. "
        "If confidence is limited, say so clearly.\n\n"
        f"Instruction:\n{instruction.strip()}\n\n"
        f"Context:\n{json.dumps(context, indent=2, default=str)}"
    )
