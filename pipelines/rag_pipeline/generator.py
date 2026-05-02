from __future__ import annotations

import json
from typing import Any

import httpx

from .config import RagSettings
from .schemas import RetrievedDocument, ShapSignal
from .text_cleaning import clean_clinical_text, clean_label_text, clean_rag_text, clean_text_list


CONDITION_BY_DISEASE = {
    "diabetes": ("Type 2 Diabetes Mellitus", "E11"),
    "hypertension": ("Essential Hypertension", "I10"),
    "cardiovascular": ("Cardiovascular Disease", "I25.9"),
    "respiratory": ("Respiratory Disorder, Unspecified", "J98.9"),
    "sleep": ("Sleep Disorder, Unspecified", "G47.9"),
}


def _clip_text(text: str, limit: int = 280) -> str:
    return clean_clinical_text(text, limit=limit)


def _confidence_risk_level(score: float) -> str:
    normalized = max(0.0, min(1.0, score / 100.0 if score > 1 else score))
    if normalized > 0.8:
        return "high"
    if normalized >= 0.5:
        return "moderate"
    return "low"


def _condition_from_documents(documents: list[RetrievedDocument]) -> tuple[str, str]:
    for doc in documents:
        key = clean_label_text(doc.disease_type).lower()
        if key in CONDITION_BY_DISEASE:
            return CONDITION_BY_DISEASE[key]
    return ("General Health Risk Assessment", "Z13.9")


def _reference_labels(documents: list[RetrievedDocument]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for doc in documents:
        source = clean_label_text(doc.source_org or doc.source, limit=100)
        title = clean_label_text(doc.title, limit=140)
        label = f"{source}: {title}" if source and title and source.lower() not in title.lower() else source or title
        key = label.lower()
        if not label or key in seen:
            continue
        seen.add(key)
        labels.append(label)
        if len(labels) >= 4:
            break
    return labels


def _source_reference(doc: RetrievedDocument) -> dict[str, str]:
    return {
        "source": doc.source,
        "title": doc.title,
        "url": doc.source_url,
    }


def _coerce_source_references(value: Any, documents: list[RetrievedDocument]) -> list[dict[str, str]]:
    allowed = [_source_reference(document) for document in documents]
    if not allowed:
        return []

    by_url = {item["url"]: item for item in allowed if item["url"]}
    by_source = {item["source"]: item for item in allowed if item["source"]}
    by_title = {item["title"]: item for item in allowed if item["title"]}
    coerced: list[dict[str, str]] = []
    items = value if isinstance(value, list) else []
    for item in items:
        reference: dict[str, str] | None = None
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            source = str(item.get("source") or "").strip()
            title = str(item.get("title") or "").strip()
            reference = by_url.get(url) or by_source.get(source) or by_title.get(title)
        else:
            text = str(item or "").strip()
            reference = by_source.get(text) or by_title.get(text) or by_url.get(text)
        if reference and reference not in coerced:
            coerced.append(reference)

    return coerced or [allowed[0]]


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

    def _ground_generated_payload(
        self,
        payload: dict[str, Any],
        documents: list[RetrievedDocument],
    ) -> dict[str, Any]:
        grounded = dict(payload)
        grounded["summary"] = clean_clinical_text(grounded.get("summary"), limit=360)
        condition, icd_code = _condition_from_documents(documents)
        grounded["condition"] = clean_label_text(grounded.get("condition") or condition, limit=120)
        grounded["icd_code"] = clean_label_text(grounded.get("icd_code") or icd_code, limit=24)
        grounded["confidence"] = max(0.0, min(1.0, float(grounded.get("confidence") or 0.0)))
        grounded["risk_level"] = clean_label_text(grounded.get("risk_level"), limit=40).lower()
        grounded["references"] = clean_text_list(grounded.get("references"), limit=4, item_limit=160) or _reference_labels(documents)
        for key in ("factors", "recommendations"):
            items = grounded.get(key)
            if not isinstance(items, list):
                grounded[key] = []
                continue
            normalized_items = []
            for item in items:
                if key == "recommendations" and isinstance(item, str):
                    detail = clean_clinical_text(item, limit=320)
                    if not detail:
                        continue
                    normalized_items.append(
                        {
                            "title": clean_label_text(detail, limit=80),
                            "detail": detail,
                            "sources": _coerce_source_references([], documents),
                        }
                    )
                    continue
                if not isinstance(item, dict):
                    continue
                normalized_item = dict(item)
                if "title" in normalized_item:
                    normalized_item["title"] = clean_label_text(normalized_item.get("title"), limit=120)
                for text_key in ("explanation", "detail", "description", "text"):
                    if text_key in normalized_item:
                        normalized_item[text_key] = clean_clinical_text(normalized_item.get(text_key), limit=320)
                normalized_item["sources"] = _coerce_source_references(item.get("sources"), documents)
                normalized_items.append(normalized_item)
            grounded[key] = normalized_items
        if "symptoms" in grounded:
            grounded["symptoms"] = clean_text_list(grounded.get("symptoms"), limit=6, item_limit=80)
        if "recommendation" in grounded:
            grounded["recommendation"] = clean_clinical_text(grounded.get("recommendation"), limit=280)
        return grounded

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
        context_blocks = []
        for index, doc in enumerate(documents, start=1):
            context_blocks.append(
                "\n".join(
                    [
                        f"[{index}] {doc.title}",
                        f"Source: {doc.source}",
                        f"URL: {doc.source_url or 'not provided'}",
                        f"Topic: {doc.topic}; Disease type: {doc.disease_type}",
                        f"Retrieval score: {doc.score:.4f}",
                        clean_rag_text(doc.text),
                    ]
                )
            )
        context = "\n\n".join(context_blocks)
        condition, icd_code = _condition_from_documents(documents)
        return f"""
You are a clinical AI assistant.

Use only the retrieved context below. Do not add facts that are not supported by the context.
If the context is incomplete, say so plainly.
Keep language cautious: never diagnose, never claim certainty, and never replace clinician care.
Every factor and recommendation must list source references from the retrieved context only.
Output must:
- Never include markdown heading markers
- Use professional medical tone
- Provide structured output ONLY
- Include ICD-style naming when possible
- Include confidence and references

Return valid JSON only with this clinical report shape. Do not use markdown headings, bullets, or raw context chunks:
{{
  "condition": "{condition}",
  "icd_code": "{icd_code}",
  "confidence": {risk_score:.4f},
  "risk_level": "{_confidence_risk_level(risk_score)}",
  "summary": "short paragraph",
  "clinical_insight": "clinically structured interpretation",
  "symptoms": ["symptom or manifestation"],
  "recommendation": "single highest priority next step",
  "references": ["source label from retrieved context"],
  "factors": [
    {{
      "feature_name": "feature id",
      "title": "human name",
      "impact": "raises risk|lowers risk",
      "explanation": "grounded explanation",
      "sources": [{{"source": "source name", "title": "document title", "url": "https://..."}}]
    }}
  ],
  "recommendations": [
    {{
      "title": "short action",
      "detail": "practical grounded advice",
      "sources": [{{"source": "source name", "title": "document title", "url": "https://..."}}]
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
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a clinical AI assistant. Return structured JSON only, never markdown. "
                                "Use only retrieved evidence, include ICD-style naming when possible, confidence, and references."
                            ),
                        },
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
        condition, icd_code = _condition_from_documents(documents)
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
                    "sources": [_source_reference(supporting_doc)],
                }
            )

        recommendations = []
        for doc in documents[:3]:
            first_sentence = doc.text.split(". ")[0].strip()
            recommendations.append(
                {
                    "title": doc.title,
                    "detail": _clip_text(first_sentence),
                    "sources": [_source_reference(doc)],
                }
            )

        factor_names = ", ".join(signal.display_name for signal in signals) or "the retrieved health drivers"
        return {
            "condition": condition,
            "icd_code": icd_code,
            "confidence": round(max(0.0, min(1.0, risk_score / 100.0 if risk_score > 1 else risk_score)), 4),
            "risk_level": _confidence_risk_level(risk_score),
            "summary": _clip_text(
                f"Risk score {risk_score:.2f} ({risk_level}) is being interpreted using retrieved medical guidance. "
                f"The strongest model drivers are {factor_names}. The explanation is limited to evidence found in {', '.join(lead_sources) or 'the indexed corpus'}."
            ),
            "clinical_insight": _clip_text(
                f"The calibrated model shows a {_confidence_risk_level(risk_score)} probability signal for {condition}. "
                "This is a screening-oriented interpretation for clinical review, not a diagnosis."
            ),
            "symptoms": [],
            "recommendation": recommendations[0]["detail"] if recommendations else "",
            "references": _reference_labels(documents),
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
                return self._ground_generated_payload(generated, documents)

        return self._fallback_response(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=signals,
            documents=documents,
        )
