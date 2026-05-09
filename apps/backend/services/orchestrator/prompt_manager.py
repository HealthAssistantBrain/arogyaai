from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPT_GROUPS = {
    "chatbot": "chatbot",
    "report_summary": "reports",
    "symptom_analysis": "symptoms",
    "recommendations": "recommendations",
    "ai_insights": "insights",
}


class PromptManager:
    def __init__(self, prompt_root: Path | None = None):
        self.prompt_root = prompt_root or Path(__file__).resolve().parents[2] / "prompts"

    @lru_cache(maxsize=16)
    def get_template(self, workflow: str, version: str = "v1") -> dict[str, Any]:
        group = PROMPT_GROUPS.get(workflow, workflow)
        path = self.prompt_root / group / f"{version}.json"
        if not path.is_file():
            return {
                "id": workflow,
                "version": version,
                "system": "You are ArogyaAI's orchestration model. Return cautious, structured JSON only.",
                "instructions": [],
                "required_output": [],
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def render(
        self,
        workflow: str,
        *,
        context: dict[str, Any],
        version: str = "v1",
        provider_name: str | None = None,
    ) -> dict[str, Any]:
        template = self.get_template(workflow, version=version)
        instructions = list(template.get("instructions") or [])
        if provider_name == "local":
            instructions.append("Keep the JSON compact and avoid long prose.")
        elif provider_name == "openai":
            instructions.append("Prefer explicit field names and normalized enums in the JSON.")

        prompt = "\n".join(
            [
                f"Workflow: {workflow}",
                *[f"- {item}" for item in instructions],
                "",
                "Context JSON:",
                json.dumps(context, indent=2, default=str),
                "",
                "Return only valid JSON.",
            ]
        ).strip()
        return {
            "template_id": template.get("id") or workflow,
            "version": template.get("version") or version,
            "system_prompt": str(template.get("system") or "").strip(),
            "required_output": template.get("required_output") or [],
            "prompt": prompt,
        }
