from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ai.conversation import ConversationIntelligenceService


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
        self.conversation = ConversationIntelligenceService()

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
        instructions.extend(self._workflow_overrides(workflow))
        if provider_name == "local":
            instructions.append("Keep the JSON compact and avoid long prose.")
        elif provider_name == "openai":
            instructions.append("Prefer explicit field names and normalized enums in the JSON.")
        elif provider_name == "nvidia":
            instructions.extend(
                [
                    "Keep each field semantically distinct to preserve long-context coherence.",
                    "Avoid repeating the same clinical disclaimer or opener across fields.",
                    "Use short, grounded sentences and return only one JSON object.",
                ]
            )

        conversation_layer = self._conversation_context(workflow, context)

        prompt = "\n".join(
            [
                f"Workflow: {workflow}",
                *[f"- {item}" for item in instructions],
                "",
                "Conversation Intelligence:",
                json.dumps(conversation_layer, indent=2, default=str),
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

    def _workflow_overrides(self, workflow: str) -> list[str]:
        shared = [
            "Vary sentence openings and transitions naturally.",
            "Explain why the finding matters, not just what it is.",
            "Keep the tone medically grounded, emotionally adaptive, and free of robotic filler.",
            "Do not copy retrieved text verbatim; synthesize it in your own words.",
        ]
        per_workflow = {
            "chatbot": [
                "Maintain multi-turn continuity and avoid asking for details already present in recent conversation.",
                "If the risk is higher, become more direct and more concise.",
            ],
            "report_summary": [
                "Translate technical findings into plain language first, then explain implications.",
            ],
            "ocr_medical_report": [
                "Translate technical findings into plain language first, then explain implications.",
            ],
            "symptom_analysis": [
                "Use triage-style follow-up questions that narrow the problem rather than generic symptom fishing.",
            ],
            "recommendations": [
                "Make recommendations feel personalized, prioritized, and practical.",
            ],
            "ai_insights": [
                "Connect data trends across time and explain which signals matter most.",
            ],
        }
        return [*shared, *(per_workflow.get(workflow, []))]

    def _conversation_context(self, workflow: str, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(context, dict):
            return {}
        user_context = context.get("user_context") if isinstance(context.get("user_context"), dict) else {}
        conversation_history = context.get("conversation_history") if isinstance(context.get("conversation_history"), list) else []
        query = str(context.get("query") or "").strip()
        response_payload = context.get("response_payload") if isinstance(context.get("response_payload"), dict) else {}
        risk_level = ""
        if isinstance(context.get("ml_data"), dict):
            risk_level = str(context["ml_data"].get("risk_level") or "")
        if not risk_level and isinstance(response_payload, dict):
            risk_level = str(response_payload.get("risk_level") or "")
        return self.conversation.prompt_context(
            workflow=workflow,
            query=query,
            user_context=user_context,
            conversation_history=conversation_history,
            response_payload=response_payload,
            risk_level=risk_level,
            conversation_intent=str(context.get("intent") or workflow),
        )
