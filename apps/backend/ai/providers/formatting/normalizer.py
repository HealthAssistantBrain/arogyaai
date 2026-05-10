from __future__ import annotations

import json
from typing import Any

from ..models.payloads import ProviderAttempt, ProviderRequest, ProviderResponse


def _extract_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class ResponseNormalizer:
    def normalize(
        self,
        *,
        request: ProviderRequest,
        provider: str,
        model: str,
        raw: dict[str, Any] | None,
        attempt: ProviderAttempt,
        fallback_used: bool = False,
        degraded: bool = False,
        streamed: bool = False,
    ) -> ProviderResponse:
        raw = raw if isinstance(raw, dict) else {}
        content = (
            _extract_json_object(raw.get("content"))
            or _extract_json_object(raw.get("payload"))
            or _extract_json_object(raw.get("text"))
            or _extract_json_object(raw.get("raw_response"))
            or {}
        )
        text = str(
            raw.get("text")
            or raw.get("raw_response")
            or content.get("message")
            or content.get("summary")
            or content.get("clinical_summary")
            or ""
        ).strip()
        citations = raw.get("citations") if isinstance(raw.get("citations"), list) else content.get("references") or content.get("sources") or []
        recommendations = content.get("recommendations") if isinstance(content.get("recommendations"), list) else []
        sections = content.get("sections") if isinstance(content.get("sections"), list) else []
        if not sections and text:
            sections = [{"title": "response", "content": text}]
        confidence = content.get("confidence_score") if content.get("confidence_score") is not None else raw.get("confidence")
        try:
            confidence_score = float(confidence or 0.0)
        except (TypeError, ValueError):
            confidence_score = 0.0

        content.setdefault("message", text or content.get("message") or "")
        content.setdefault("summary", content.get("summary") or content.get("clinical_summary") or text)
        content.setdefault("clinical_summary", content.get("clinical_summary") or content.get("summary") or text)
        content.setdefault("clinical_interpretation", content.get("clinical_interpretation") or content.get("clinical_summary") or text)
        content.setdefault("recommendations", recommendations)
        content.setdefault("references", citations if isinstance(citations, list) else [])

        tokens = raw.get("tokens") if isinstance(raw.get("tokens"), dict) else raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        return ProviderResponse(
            success=bool(content),
            provider=provider,
            model=model,
            task=request.task,
            workflow=request.workflow,
            status="ready" if content else "empty",
            content=content,
            text=text,
            sections=sections,
            citations=[item for item in citations if isinstance(item, dict)] if isinstance(citations, list) else [],
            recommendations=[str(item).strip() for item in recommendations if str(item).strip()],
            confidence=max(0.0, min(1.0, confidence_score)),
            attempts=[attempt],
            latency_ms=attempt.latency_ms,
            tokens=dict(tokens),
            degraded=degraded,
            streamed=streamed,
            fallback_used=fallback_used,
            safe=True,
            warnings=[],
            metadata={},
            raw=raw,
        )
