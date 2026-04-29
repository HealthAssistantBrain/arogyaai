from __future__ import annotations

import json
from typing import Any

import httpx

from .config import RagSettings
from .schemas import RetrievedDocument, ShapSignal


def _clip_text(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


class ExplanationGenerator:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def _build_prompt(
        self,
        *,
        risk_score: float,
        risk_level: str,
        signals: list[ShapSignal],
        documents: list[RetrievedDocument],
    ) -> str:
        factors = "\n".join(
            f"- {signal.display_name}: shap={signal.shap_value:.4f}, direction={signal.direction}, value={signal.feature_value}"
            for signal in signals
        )
        context = "\n\n".join(
            f"[{index}] {doc.title} ({doc.source}, {doc.category})\n{doc.text}"
            for index, doc in enumerate(documents, start=1)
        )
        return f"""
You are a medical AI assistant.

Use only the retrieved context below. Do not add facts that are not supported by the context.
If the context is incomplete, say so plainly.
Return valid JSON only with this shape:
{{
  "summary": "short paragraph",
  "factors": [
    {{
      "feature_name": "feature id",
      "title": "human name",
      "impact": "raises risk|lowers risk",
      "explanation": "grounded explanation",
      "sources": ["file.md"]
    }}
  ],
  "recommendations": [
    {{
      "title": "short action",
      "detail": "practical grounded advice",
      "sources": ["file.md"]
    }}
  ]
}}

User risk score: {risk_score:.4f}
Risk level: {risk_level}
Top contributing factors:
{factors}

Context:
{context}
""".strip()

    async def _generate_with_ollama(self, prompt: str) -> dict[str, Any] | None:
        if not self.settings.ollama_base_url:
            return None

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = response.json()
            return _extract_json_object(str(payload.get("response") or ""))

    async def _generate_with_api(self, prompt: str) -> dict[str, Any] | None:
        if not self.settings.llm_api_base or not self.settings.llm_api_key:
            return None

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.llm_api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_api_model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": "You produce grounded medical explanations from retrieved evidence only."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices") or []
            if not choices:
                return None
            message = (choices[0].get("message") or {}).get("content") or ""
            return _extract_json_object(message)

    def _fallback_response(
        self,
        *,
        risk_score: float,
        risk_level: str,
        signals: list[ShapSignal],
        documents: list[RetrievedDocument],
    ) -> dict[str, Any]:
        lead_sources = [doc.source for doc in documents[:2]]
        factor_payload = []
        for index, signal in enumerate(signals):
            supporting_doc = documents[min(index, len(documents) - 1)]
            factor_payload.append(
                {
                    "feature_name": signal.feature_name,
                    "title": signal.display_name,
                    "impact": "raises risk" if signal.shap_value >= 0 else "lowers risk",
                    "explanation": _clip_text(
                        f"{signal.display_name} is one of the strongest model drivers in this prediction. "
                        f"Retrieved guidance links this area to cardiometabolic risk: {supporting_doc.text}"
                    ),
                    "sources": [supporting_doc.source],
                }
            )

        recommendations = []
        for doc in documents[:3]:
            first_sentence = doc.text.split(". ")[0].strip()
            recommendations.append(
                {
                    "title": doc.title,
                    "detail": _clip_text(first_sentence),
                    "sources": [doc.source],
                }
            )

        factor_names = ", ".join(signal.display_name for signal in signals) or "the retrieved health drivers"
        return {
            "summary": _clip_text(
                f"Risk score {risk_score:.2f} ({risk_level}) is being interpreted using retrieved medical guidance. "
                f"The strongest model drivers are {factor_names}. The explanation is limited to evidence found in {', '.join(lead_sources) or 'the indexed corpus'}."
            ),
            "factors": factor_payload,
            "recommendations": recommendations,
        }

    async def generate(
        self,
        *,
        risk_score: float,
        risk_level: str,
        signals: list[ShapSignal],
        documents: list[RetrievedDocument],
    ) -> dict[str, Any]:
        if not documents:
            raise RuntimeError("Explanation generation requires retrieved documents.")

        prompt = self._build_prompt(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=signals,
            documents=documents,
        )

        for generator in (self._generate_with_ollama, self._generate_with_api):
            try:
                generated = await generator(prompt)
            except Exception:
                generated = None
            if generated:
                return generated

        return self._fallback_response(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=signals,
            documents=documents,
        )
