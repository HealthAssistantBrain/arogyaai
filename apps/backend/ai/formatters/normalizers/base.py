from __future__ import annotations

from dataclasses import dataclass, field
import ast
import json
import re
from typing import Any


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass(slots=True)
class NormalizedOutput:
    payload: dict[str, Any]
    text: str = ""
    raw_response_text: str = ""
    repairs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ProviderResponseNormalizer:
    provider_name = "default"

    def normalize(self, *, raw_response: Any, payload: dict[str, Any] | None = None, workflow: str = "") -> NormalizedOutput:
        merged = self._merge_payload(raw_response, payload or {})
        raw_response_text = self._serialize_raw(raw_response)
        text = self._resolve_text(raw_response, merged)
        cleaned_text = self._clean_markdown(text)
        repairs: list[str] = []
        if isinstance(raw_response, dict):
            raw_text = self._first_text(raw_response.get("text"), raw_response.get("raw_response"), raw_response.get("message"))
            if raw_text and self._strip_fences(raw_text) != raw_text.strip():
                repairs.append("markdown_cleanup")
        if cleaned_text and cleaned_text != text:
            if "markdown_cleanup" not in repairs:
                repairs.append("markdown_cleanup")
        if cleaned_text and "structured_sections" not in merged and "sections" not in merged:
            extracted_sections = self._extract_markdown_sections(cleaned_text)
            if extracted_sections:
                merged["structured_sections"] = extracted_sections
                repairs.append("hallucinated_heading_normalized")
        merged["summary"] = self._first_text(
            merged.get("summary"),
            merged.get("message"),
            merged.get("clinical_summary"),
            merged.get("patient_summary"),
            cleaned_text,
        )
        merged["message"] = self._first_text(merged.get("message"), merged.get("summary"), cleaned_text)
        merged["confidence_score"] = self._normalize_confidence(
            merged.get("confidence_score"),
            merged.get("confidence"),
            merged.get("confidence_label"),
        )
        merged["citations"] = self._coerce_reference_list(
            merged.get("citations") or merged.get("references") or merged.get("sources")
        )
        merged["warnings"] = self._normalize_string_list(merged.get("warnings"))
        if "sections" in merged and "structured_sections" not in merged:
            merged["structured_sections"] = self._coerce_section_list(merged.get("sections"))
        merged["structured_sections"] = self._dedupe_sections(
            self._coerce_section_list(merged.get("structured_sections"))
        )
        return NormalizedOutput(
            payload=merged,
            text=cleaned_text or merged.get("summary") or "",
            raw_response_text=raw_response_text,
            repairs=repairs,
            warnings=[],
        )

    def _merge_payload(self, raw_response: Any, payload: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for candidate in self._candidate_values(raw_response):
            parsed = self._parse_candidate(candidate)
            if parsed:
                merged.update(parsed)
        merged.update(_safe_dict(payload))
        return merged

    def _candidate_values(self, raw_response: Any) -> list[Any]:
        if isinstance(raw_response, dict):
            return [
                raw_response,
                raw_response.get("payload"),
                raw_response.get("content"),
                raw_response.get("message"),
                raw_response.get("text"),
                raw_response.get("raw_response"),
            ]
        return [raw_response]

    def _parse_candidate(self, candidate: Any) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        if isinstance(candidate, list):
            return {}
        text = _safe_text(candidate)
        if not text:
            return {}
        extracted = self._extract_json_block(text)
        if extracted is not None:
            return extracted
        return {}

    def _extract_json_block(self, text: str) -> dict[str, Any] | None:
        stripped = self._strip_fences(text)
        if not stripped:
            return None
        for candidate in (stripped, self._balanced_brace_block(stripped)):
            parsed = self._try_parse_json(candidate)
            if parsed is not None:
                return parsed
        return None

    def _try_parse_json(self, text: str | None) -> dict[str, Any] | None:
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(text)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, SyntaxError):
            return None

    def _serialize_raw(self, raw_response: Any) -> str:
        if raw_response is None:
            return ""
        if isinstance(raw_response, str):
            return raw_response.strip()
        try:
            return json.dumps(raw_response, default=str)
        except TypeError:
            return _safe_text(raw_response)

    def _resolve_text(self, raw_response: Any, merged: dict[str, Any]) -> str:
        return self._first_text(
            merged.get("message"),
            merged.get("summary"),
            merged.get("clinical_summary"),
            merged.get("patient_summary"),
            raw_response.get("text") if isinstance(raw_response, dict) else "",
            raw_response.get("raw_response") if isinstance(raw_response, dict) else "",
        )

    def _strip_fences(self, text: str) -> str:
        stripped = re.sub(r"^```(?:json|markdown|md)?\s*", "", text.strip(), flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    def _balanced_brace_block(self, text: str) -> str | None:
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        last_index = -1
        for index, char in enumerate(text[start:], start=start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    last_index = index
                    break
        if last_index <= start:
            return None
        return text[start : last_index + 1]

    def _clean_markdown(self, text: str) -> str:
        if not text:
            return ""
        value = self._strip_fences(text)
        value = re.sub(r"^#+\s*", "", value, flags=re.MULTILINE)
        value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
        value = re.sub(r"__(.*?)__", r"\1", value)
        value = re.sub(r"`([^`]*)`", r"\1", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        cleaned_lines = []
        for line in value.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            stripped = re.sub(r"^[-*•]\s+", "", stripped)
            cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines).strip()

    def _extract_markdown_sections(self, text: str) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        current_title = "response"
        current_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append("")
                continue
            heading_match = re.match(r"^(?:#{1,6}\s*)?([A-Za-z][A-Za-z /-]{2,40})\s*:\s*$", stripped)
            if heading_match and len(current_lines) > 0:
                sections.append(self._build_section(current_title, current_lines))
                current_title = heading_match.group(1)
                current_lines = []
                continue
            if heading_match and not current_lines:
                current_title = heading_match.group(1)
                continue
            current_lines.append(re.sub(r"^[-*•]\s+", "", stripped))
        if current_lines:
            sections.append(self._build_section(current_title, current_lines))
        return [section for section in sections if section.get("content") or section.get("bullets")]

    def _build_section(self, title: str, lines: list[str]) -> dict[str, Any]:
        bullets = [line for line in lines if line and len(line.split()) <= 18]
        content = " ".join(line for line in lines if line).strip()
        return {
            "key": re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "section",
            "title": title.strip(),
            "content": content,
            "bullets": bullets[:6],
        }

    def _normalize_confidence(self, *values: Any) -> float:
        for value in values:
            if isinstance(value, (int, float)):
                numeric = float(value)
                return max(0.0, min(1.0, numeric / 100.0 if numeric > 1 else numeric))
            text = _safe_text(value).lower()
            if not text:
                continue
            if any(token in text for token in ("very high", "high confidence")):
                return 0.85
            if any(token in text for token in ("moderate", "medium")):
                return 0.65
            if any(token in text for token in ("low", "uncertain")):
                return 0.4
        return 0.0

    def _coerce_reference_list(self, value: Any) -> list[dict[str, Any]]:
        references: list[dict[str, Any]] = []
        for item in _safe_list(value):
            if isinstance(item, dict):
                references.append(dict(item))
            else:
                text = _safe_text(item)
                if text:
                    references.append({"title": text})
        return references

    def _normalize_string_list(self, value: Any) -> list[str]:
        items = value if isinstance(value, list) else [value] if value else []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = self._clean_markdown(_safe_text(item))
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                normalized.append(text)
        return normalized

    def _coerce_section_list(self, value: Any) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        for item in _safe_list(value):
            if isinstance(item, dict):
                title = self._first_text(item.get("title"), item.get("heading"), item.get("key"), "Section")
                sections.append(
                    {
                        "key": re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "section",
                        "title": title,
                        "content": self._clean_markdown(_safe_text(item.get("content") or item.get("body"))),
                        "bullets": self._normalize_string_list(item.get("bullets") or item.get("items")),
                    }
                )
            else:
                text = self._clean_markdown(_safe_text(item))
                if text:
                    sections.append({"key": "response", "title": "Response", "content": text, "bullets": []})
        return sections

    def _dedupe_sections(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for section in sections:
            title = _safe_text(section.get("title")).lower()
            content = _safe_text(section.get("content")).lower()
            key = f"{title}|{content}"
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(section)
        return normalized

    def _first_text(self, *values: Any) -> str:
        for value in values:
            text = _safe_text(value)
            if text:
                return text
        return ""
