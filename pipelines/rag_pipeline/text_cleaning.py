from __future__ import annotations

import re
from dataclasses import replace
from typing import Any


_SENTENCE_ENDINGS = ".!?"
_SECTION_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s*(?P<title>[^#\n]+?)\s*#*\s*$")
_LIST_PREFIX_RE = re.compile(r"(?m)^\s*[-*+]\s+")


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _strip_markdown(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*(.*?)\s*#*\s*$", r"\1.", text)
    text = re.sub(r"(^|\s)#{1,6}\s?", ". ", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"[*`]+", "", text)
    return text.replace("_", " ")


def _normalize_spacing(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\s*\n+\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    text = re.sub(r"\s*([.!?])\s*([.!?])\s*", r"\1 ", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    return text.strip(" \t\r\n.-:;")


def _capitalize_sentences(text: str) -> str:
    def replace_match(match: re.Match[str]) -> str:
        prefix, letter = match.groups()
        return f"{prefix}{letter.upper()}"

    return re.sub(r"(^|[.!?]\s+)([a-z])", replace_match, text)


def _trim_trailing_fragment(text: str) -> str:
    if not text:
        return ""
    if text[-1] in _SENTENCE_ENDINGS:
        return text

    matches = list(re.finditer(r"[.!?](?=\s|$)", text))
    if matches:
        tail = text[matches[-1].end() :].strip()
        if 0 < len(tail.split()) <= 10:
            return text[: matches[-1].end()].strip()

    return text.rstrip(" ,;:")


def _clip_to_sentence(text: str, limit: int | None) -> str:
    if not limit or len(text) <= limit:
        return text

    clipped = text[:limit].rstrip(" ,;:")
    matches = list(re.finditer(r"[.!?](?=\s|$)", clipped))
    if matches and matches[-1].end() >= max(48, limit // 3):
        return clipped[: matches[-1].end()].strip()
    return clipped


def ensure_sentence_end(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text[-1] in _SENTENCE_ENDINGS:
        return text
    return f"{text}."


def clean_clinical_text(
    value: Any,
    *,
    limit: int | None = None,
    ensure_sentence: bool = True,
) -> str:
    text = _coerce_text(value)
    if not text:
        return ""

    text = _strip_markdown(text)
    text = _normalize_spacing(text)
    text = _trim_trailing_fragment(text)
    text = _clip_to_sentence(text, limit)
    text = _trim_trailing_fragment(text)
    text = _capitalize_sentences(text)
    if ensure_sentence:
        text = ensure_sentence_end(text)
    return text


def clean_label_text(value: Any, *, limit: int | None = None) -> str:
    text = clean_clinical_text(value, limit=limit, ensure_sentence=False)
    return text.rstrip(_SENTENCE_ENDINGS)


def clean_text_list(
    value: Any,
    *,
    limit: int | None = None,
    item_limit: int | None = 180,
    ensure_sentence: bool = False,
) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, str):
        items = re.split(r"(?<=[.!?])\s+|,\s+", value)
    else:
        items = []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = clean_clinical_text(item, limit=item_limit, ensure_sentence=ensure_sentence)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if limit and len(cleaned) >= limit:
            break
    return cleaned


def clean_rag_text(value: Any, *, limit: int | None = None) -> str:
    return clean_clinical_text(value, limit=limit, ensure_sentence=True)


def clean_source_payload(item: Any, *, text_limit: int = 640, excerpt_limit: int = 280) -> dict[str, Any]:
    payload = dict(item) if isinstance(item, dict) else {}
    cleaned = dict(payload)
    for key in ("source", "source_org", "category", "topic", "disease_type", "retrieval_method", "condition", "severity"):
        if key in cleaned:
            cleaned[key] = clean_label_text(cleaned.get(key), limit=120)
    for key in ("title",):
        if key in cleaned:
            cleaned[key] = clean_label_text(cleaned.get(key), limit=140)
    if "text" in cleaned:
        cleaned["text"] = clean_rag_text(cleaned.get("text"), limit=text_limit)
    if "excerpt" in cleaned:
        cleaned["excerpt"] = clean_rag_text(cleaned.get("excerpt"), limit=excerpt_limit)
    elif cleaned.get("text"):
        cleaned["excerpt"] = clean_rag_text(cleaned.get("text"), limit=excerpt_limit)
    if isinstance(cleaned.get("citation"), dict):
        citation = dict(cleaned["citation"])
        citation["source"] = clean_label_text(citation.get("source"), limit=120)
        citation["title"] = clean_label_text(citation.get("title"), limit=140)
        cleaned["citation"] = citation
    for key in ("symptoms", "risk_factors"):
        if key in cleaned:
            cleaned[key] = clean_text_list(cleaned.get(key), limit=8, item_limit=120)
    return cleaned


def normalize_heading(value: Any, *, fallback: str = "Overview") -> str:
    return clean_label_text(value, limit=120) or fallback


def _section_buckets(markdown_text: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {"overview": []}
    current = "overview"
    for raw_line in markdown_text.splitlines():
        heading = _SECTION_HEADING_RE.match(raw_line)
        if heading:
            current = normalize_heading(heading.group("title")).lower()
            buckets.setdefault(current, [])
            continue
        buckets.setdefault(current, []).append(raw_line)
    return buckets


def _extract_section_items(buckets: dict[str, list[str]], *tokens: str, limit: int = 8) -> list[str]:
    matched_lines: list[str] = []
    for heading, lines in buckets.items():
        if any(token in heading for token in tokens):
            matched_lines.extend(
                _LIST_PREFIX_RE.sub("", line).strip()
                for line in lines
                if line.strip()
            )
    return clean_text_list(matched_lines, limit=limit, item_limit=120)


def extract_clinical_fields(markdown_text: Any, *, fallback_condition: str = "") -> dict[str, Any]:
    raw_text = _coerce_text(markdown_text)
    buckets = _section_buckets(raw_text)
    condition = normalize_heading(fallback_condition or next(iter(buckets.keys()), "General health"))
    symptoms = _extract_section_items(buckets, "symptom", "manifestation", "sign")
    risk_factors = _extract_section_items(buckets, "risk factor", "risk factors", "risk", "causes")
    cleaned_text = clean_rag_text(raw_text)
    return {
        "condition": condition,
        "symptoms": symptoms,
        "risk_factors": risk_factors,
        "text": cleaned_text,
    }


def clean_retrieved_document(document: Any) -> Any:
    return replace(
        document,
        text=clean_rag_text(getattr(document, "text", "")),
        title=clean_label_text(getattr(document, "title", ""), limit=140),
        source=clean_label_text(getattr(document, "source", ""), limit=140),
        source_org=clean_label_text(getattr(document, "source_org", ""), limit=140),
        category=clean_label_text(getattr(document, "category", ""), limit=80),
        topic=clean_label_text(getattr(document, "topic", ""), limit=120),
        disease_type=clean_label_text(getattr(document, "disease_type", ""), limit=80),
        severity=clean_label_text(getattr(document, "severity", "routine"), limit=40),
    )
