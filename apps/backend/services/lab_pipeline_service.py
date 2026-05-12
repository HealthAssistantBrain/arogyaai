"""Canonical lab extraction pipeline.

Processes OCR/PDF report text into structured lab result rows with LOINC
mapping, confidence, source text, source type, and page provenance.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.pipeline_logger import log_pipeline
from database.session import SessionLocal
from models import Report, User

logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class LabDefinition:
    key: str
    name: str
    loinc_code: str
    category: str
    unit: str
    reference_range: str
    aliases: tuple[str, ...]


_LAB_CATALOG: tuple[LabDefinition, ...] = (
    LabDefinition("hemoglobin", "Hemoglobin", "718-7", "hematology", "g/dL", "13.5 - 17.5", ("hemoglobin", "haemoglobin", "hb", "hgb")),
    LabDefinition("wbc", "WBC", "6690-2", "hematology", "x10^3/uL", "4.0 - 11.0", ("wbc", "white blood cell", "white blood cells", "total leukocyte count", "tlc", "leukocyte count")),
    LabDefinition("rbc", "RBC", "789-8", "hematology", "x10^6/uL", "4.5 - 5.9", ("rbc", "red blood cell", "red blood cells", "erythrocyte count")),
    LabDefinition("platelets", "Platelets", "777-3", "hematology", "x10^3/uL", "150 - 450", ("platelet", "platelets", "platelet count", "plt")),
    LabDefinition("hematocrit", "Hematocrit", "4544-3", "hematology", "%", "41 - 53", ("hematocrit", "haematocrit", "hct", "pcv", "packed cell volume")),
    LabDefinition("mcv", "MCV", "787-2", "hematology", "fL", "80 - 100", ("mcv", "mean corpuscular volume")),
    LabDefinition("mch", "MCH", "785-6", "hematology", "pg", "27 - 33", ("mch", "mean corpuscular hemoglobin")),
    LabDefinition("mchc", "MCHC", "786-4", "hematology", "g/dL", "32 - 36", ("mchc", "mean corpuscular hemoglobin concentration")),
    LabDefinition("neutrophils", "Neutrophils", "770-8", "hematology", "%", "40 - 70", ("neutrophils", "neutrophil")),
    LabDefinition("lymphocytes", "Lymphocytes", "736-9", "hematology", "%", "20 - 40", ("lymphocytes", "lymphocyte")),
    LabDefinition("monocytes", "Monocytes", "5905-5", "hematology", "%", "2 - 8", ("monocytes", "monocyte")),
    LabDefinition("eosinophils", "Eosinophils", "713-8", "hematology", "%", "1 - 6", ("eosinophils", "eosinophil")),
    LabDefinition("basophils", "Basophils", "706-2", "hematology", "%", "0 - 2", ("basophils", "basophil")),
    LabDefinition("glucose_fasting", "Glucose (Fasting)", "1558-6", "metabolic", "mg/dL", "70 - 99", ("fasting glucose", "glucose fasting", "blood glucose fasting", "fasting blood sugar", "fbs")),
    LabDefinition("glucose_random", "Glucose (Random)", "2345-7", "metabolic", "mg/dL", "70 - 140", ("random glucose", "random blood sugar", "rbs", "blood glucose", "glucose")),
    LabDefinition("hba1c", "HbA1c", "4548-4", "metabolic", "%", "< 5.7", ("hba1c", "hb a1c", "a1c", "glycated hemoglobin", "glycosylated hemoglobin")),
    LabDefinition("creatinine", "Creatinine", "2160-0", "biochemistry", "mg/dL", "0.7 - 1.3", ("creatinine", "serum creatinine")),
    LabDefinition("urea", "Urea", "3094-0", "biochemistry", "mg/dL", "7 - 20", ("urea", "blood urea")),
    LabDefinition("bun", "Blood Urea Nitrogen", "3094-0", "biochemistry", "mg/dL", "7 - 20", ("bun", "blood urea nitrogen")),
    LabDefinition("uric_acid", "Uric Acid", "3084-1", "biochemistry", "mg/dL", "3.5 - 7.2", ("uric acid", "serum uric acid")),
    LabDefinition("sodium", "Sodium", "2951-2", "biochemistry", "mmol/L", "135 - 145", ("sodium", "na", "na+")),
    LabDefinition("potassium", "Potassium", "2823-3", "biochemistry", "mmol/L", "3.5 - 5.1", ("potassium", "k", "k+")),
    LabDefinition("chloride", "Chloride", "2075-0", "biochemistry", "mmol/L", "98 - 107", ("chloride", "cl", "cl-")),
    LabDefinition("calcium", "Calcium", "17861-6", "biochemistry", "mg/dL", "8.6 - 10.2", ("calcium", "serum calcium")),
    LabDefinition("total_protein", "Total Protein", "2885-2", "biochemistry", "g/dL", "6.0 - 8.3", ("total protein", "protein total")),
    LabDefinition("albumin", "Albumin", "1751-7", "biochemistry", "g/dL", "3.5 - 5.0", ("albumin", "serum albumin")),
    LabDefinition("bilirubin_total", "Bilirubin Total", "1975-2", "biochemistry", "mg/dL", "0.2 - 1.2", ("total bilirubin", "bilirubin total", "bilirubin")),
    LabDefinition("bilirubin_direct", "Bilirubin Direct", "1968-7", "biochemistry", "mg/dL", "0.0 - 0.3", ("direct bilirubin", "bilirubin direct")),
    LabDefinition("alt", "ALT / SGPT", "1742-6", "biochemistry", "U/L", "7 - 56", ("alt", "sgpt", "alanine aminotransferase")),
    LabDefinition("ast", "AST / SGOT", "1920-8", "biochemistry", "U/L", "10 - 40", ("ast", "sgot", "aspartate aminotransferase")),
    LabDefinition("alkaline_phosphatase", "Alkaline Phosphatase", "6768-6", "biochemistry", "U/L", "44 - 147", ("alkaline phosphatase", "alp")),
    LabDefinition("ggt", "GGT", "2324-2", "biochemistry", "U/L", "9 - 48", ("ggt", "gamma gt", "gamma glutamyl transferase")),
    LabDefinition("cholesterol_total", "Total Cholesterol", "2093-3", "lipid", "mg/dL", "< 200", ("total cholesterol", "cholesterol total", "cholesterol")),
    LabDefinition("ldl", "LDL Cholesterol", "13457-7", "lipid", "mg/dL", "< 100", ("ldl", "ldl cholesterol", "low density lipoprotein")),
    LabDefinition("hdl", "HDL Cholesterol", "2085-9", "lipid", "mg/dL", "> 40", ("hdl", "hdl cholesterol", "high density lipoprotein")),
    LabDefinition("triglycerides", "Triglycerides", "2571-8", "lipid", "mg/dL", "< 150", ("triglyceride", "triglycerides", "tg")),
    LabDefinition("vldl", "VLDL Cholesterol", "13458-5", "lipid", "mg/dL", "5 - 40", ("vldl", "vldl cholesterol")),
    LabDefinition("tsh", "TSH", "3016-3", "thyroid", "uIU/mL", "0.4 - 4.0", ("tsh", "thyroid stimulating hormone")),
    LabDefinition("t3", "T3", "3053-6", "thyroid", "ng/dL", "80 - 180", ("t3", "tri-iodothyronine", "triiodothyronine")),
    LabDefinition("t4", "T4", "3026-2", "thyroid", "ug/dL", "4.5 - 12.0", ("t4", "thyroxine")),
    LabDefinition("vitamin_d", "Vitamin D", "62292-8", "biochemistry", "ng/mL", "30 - 100", ("vitamin d", "25-oh vitamin d", "25 hydroxy vitamin d")),
    LabDefinition("vitamin_b12", "Vitamin B12", "2132-9", "biochemistry", "pg/mL", "200 - 900", ("vitamin b12", "b12", "cobalamin")),
    LabDefinition("ferritin", "Ferritin", "2276-4", "biochemistry", "ng/mL", "30 - 400", ("ferritin", "serum ferritin")),
    LabDefinition("crp", "C-Reactive Protein", "1988-5", "biochemistry", "mg/L", "< 5", ("crp", "c reactive protein", "c-reactive protein")),
    LabDefinition("esr", "ESR", "4537-7", "hematology", "mm/hr", "0 - 20", ("esr", "erythrocyte sedimentation rate")),
)

_LAB_DEFINITIONS: list[dict[str, Any]] = [definition.__dict__ for definition in _LAB_CATALOG]

_UNIT_ALIASES: dict[str, tuple[str, ...]] = {
    "g/dL": ("g/dl", "gm/dl", "g%", "g dl"),
    "x10^3/uL": ("x10^3/ul", "10^3/ul", "k/ul", "thousand/ul", "/mm3", "cells/ul", "cumm"),
    "x10^6/uL": ("x10^6/ul", "10^6/ul", "million/ul", "m/ul"),
    "mg/dL": ("mg/dl", "mg %", "mgdl"),
    "%": ("%", "percent"),
    "uIU/mL": ("uiu/ml", "miu/l", "u iu/ml", "micro iu/ml"),
    "mmol/L": ("mmol/l", "meq/l"),
    "U/L": ("u/l", "iu/l", "units/l"),
    "ng/mL": ("ng/ml",),
    "pg/mL": ("pg/ml",),
    "mg/L": ("mg/l",),
    "mm/hr": ("mm/hr", "mm/h", "mm 1st hr"),
    "fL": ("fl",),
    "pg": ("pg",),
    "ug/dL": ("ug/dl", "mcg/dl"),
    "ng/dL": ("ng/dl",),
}

_VALUE_RE = re.compile(r"(?<![A-Za-z0-9])(?P<value>[<>]?\s*\d+(?:\.\d+)?)")
_REFERENCE_RE = re.compile(r"(?P<ref>[<>]=?\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?)", re.IGNORECASE)
_PAGE_HEADER_RE = re.compile(r"^---\s*Page\s+(?P<page>\d+)\s+(?P<source>[A-Za-z_ -]+?)\s*---$", re.IGNORECASE)


def _normalize_text(value: str) -> str:
    text = re.sub(r"[^a-z0-9+%./ -]+", " ", (value or "").lower())
    text = re.sub(r"\b(result|results|value|observed|reference|range|unit|flag|normal|low|high)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+]+", _normalize_text(value)))


def _alias_matches(candidate: str, alias: str) -> bool:
    candidate_norm = _normalize_text(candidate)
    alias_norm = _normalize_text(alias)
    if not candidate_norm or not alias_norm:
        return False
    if alias_norm == candidate_norm:
        return True
    if len(alias_norm) <= 3:
        return alias_norm in _tokens(candidate_norm)
    return alias_norm in candidate_norm or candidate_norm in alias_norm


def map_loinc(test_name: str) -> tuple[LabDefinition | None, float]:
    """Map a reported test name to a LOINC-backed catalog entry."""
    normalized = _normalize_text(test_name)
    if not normalized:
        return None, 0.0

    best_definition: LabDefinition | None = None
    best_score = 0.0
    for definition in _LAB_CATALOG:
        names = (definition.name, definition.key, *definition.aliases)
        for alias in names:
            alias_norm = _normalize_text(alias)
            if _alias_matches(normalized, alias_norm):
                score = 0.98 if alias_norm == normalized else 0.92
            else:
                score = SequenceMatcher(None, normalized, alias_norm).ratio()
            if score > best_score:
                best_definition = definition
                best_score = score

    if best_score >= 0.78:
        return best_definition, best_score
    return None, best_score


def _normalize_source_type(source_type: str | None) -> str:
    lowered = str(source_type or "").strip().lower()
    if "ocr" in lowered:
        return "OCR"
    if "pdf" in lowered:
        return "PDF"
    return "OCR" if lowered in {"image", "jpg", "jpeg", "png"} else (source_type or "PDF")


def _classify_status(value: float, reference_range: str) -> str:
    normalized = (reference_range or "").strip()

    lt = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if lt:
        threshold = float(lt.group(1))
        if value <= threshold:
            return "normal"
        return "borderline" if value <= threshold * 1.15 else "high"

    gt = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if gt:
        threshold = float(gt.group(1))
        if value >= threshold:
            return "normal"
        return "borderline" if value >= threshold * 0.85 else "low"

    rng = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:-|to)\s*([0-9]+(?:\.[0-9]+)?)$", normalized, re.IGNORECASE)
    if rng:
        low, high = float(rng.group(1)), float(rng.group(2))
        if low <= value <= high:
            return "normal"
        band = max((high - low) * 0.1, 0.1)
        if value < low:
            return "borderline" if value >= low - band else "low"
        return "borderline" if value <= high + band else "high"

    return "normal"


def _coerce_value(raw: str) -> float | None:
    try:
        return float(str(raw or "").replace("<", "").replace(">", "").strip())
    except (TypeError, ValueError):
        return None


def _extract_unit(text: str, default_unit: str) -> tuple[str, bool]:
    lowered = (text or "").lower()
    for canonical, aliases in _UNIT_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return canonical, True
    return default_unit, False


def _extract_reference(text: str, default_reference: str) -> tuple[str, bool]:
    matches = list(_REFERENCE_RE.finditer(text or ""))
    if len(matches) >= 2:
        return matches[-1].group("ref").replace("to", "-").strip(), True
    if len(matches) == 1 and any(marker in (text or "").lower() for marker in ("ref", "range", "normal")):
        return matches[0].group("ref").replace("to", "-").strip(), True
    return default_reference, False


def _clean_test_name(value: str) -> str:
    text = re.sub(r"[:|]+", " ", value or "")
    text = re.sub(r"\b(test|investigation|parameter|analyte|result|value|unit|reference|range)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text


def _split_columns(line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*\|\s*|\t+|\s{2,}", line) if part.strip()]


def _line_looks_like_header(line: str) -> bool:
    lowered = line.lower()
    header_terms = sum(term in lowered for term in ("test", "parameter", "result", "value", "unit", "reference"))
    return header_terms >= 3 and not _VALUE_RE.search(line)


def _candidate_from_columns(line: str) -> dict[str, Any] | None:
    columns = _split_columns(line)
    if len(columns) < 2:
        return None

    for index, column in enumerate(columns):
        value_match = _VALUE_RE.search(column)
        if not value_match:
            continue
        test_name = _clean_test_name(" ".join(columns[:index]) or columns[0])
        if not test_name or _VALUE_RE.search(test_name):
            continue
        after = " ".join(columns[index:])
        value = _coerce_value(value_match.group("value"))
        if value is None:
            continue
        return {
            "test_name": test_name,
            "raw_value": value,
            "context": line,
            "value_start": line.find(value_match.group(0)),
            "value_end": line.find(value_match.group(0)) + len(value_match.group(0)),
            "unit_context": after,
            "reference_context": after,
            "method": "structured_table",
        }

    return None


def _candidate_from_line(line: str) -> dict[str, Any] | None:
    for match in _VALUE_RE.finditer(line):
        test_name = _clean_test_name(line[: match.start()])
        if len(test_name) < 2:
            continue

        value = _coerce_value(match.group("value"))
        if value is None:
            continue

        return {
            "test_name": test_name,
            "raw_value": value,
            "context": line,
            "value_start": match.start(),
            "value_end": match.end(),
            "unit_context": line[match.end() :],
            "reference_context": line[match.end() :],
            "method": "structured_line",
        }

    return None


def _bbox_number(bbox: dict[str, Any] | None, key: str) -> float:
    try:
        return float((bbox or {}).get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bbox_center_y(word: dict[str, Any]) -> float:
    bbox = word.get("bbox") if isinstance(word, dict) else None
    return (_bbox_number(bbox, "y_min") + _bbox_number(bbox, "y_max")) / 2.0


def _bbox_height(word: dict[str, Any]) -> float:
    bbox = word.get("bbox") if isinstance(word, dict) else None
    return max(_bbox_number(bbox, "y_max") - _bbox_number(bbox, "y_min"), 1.0)


def _union_bboxes(boxes: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    valid = [box for box in boxes if isinstance(box, dict)]
    if not valid:
        return None
    x_values = [float(box[key]) for box in valid for key in ("x_min", "x_max") if box.get(key) is not None]
    y_values = [float(box[key]) for box in valid for key in ("y_min", "y_max") if box.get(key) is not None]
    if not x_values or not y_values:
        return None
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    return {
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_max,
        "y_max": y_max,
        "vertices": [
            {"x": x_min, "y": y_min},
            {"x": x_max, "y": y_min},
            {"x": x_max, "y": y_max},
            {"x": x_min, "y": y_max},
        ],
    }


def _word_confidence(words: list[dict[str, Any]]) -> float | None:
    scores: list[float] = []
    for word in words:
        try:
            score = float(word.get("confidence"))
        except (TypeError, ValueError):
            continue
        scores.append(max(0.0, min(1.0, score)))
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def _layout_rows_from_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_words = [
        word for word in words
        if isinstance(word, dict) and str(word.get("text") or "").strip()
    ]
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(normalized_words, key=lambda item: (_bbox_center_y(item), _bbox_number(item.get("bbox"), "x_min"))):
        center_y = _bbox_center_y(word)
        tolerance = max(_bbox_height(word) * 0.7, 8.0)
        target: list[dict[str, Any]] | None = None
        for row in rows:
            row_center = sum(_bbox_center_y(item) for item in row) / max(len(row), 1)
            if abs(center_y - row_center) <= tolerance:
                target = row
                break
        if target is None:
            rows.append([word])
        else:
            target.append(word)

    layout_rows: list[dict[str, Any]] = []
    for row in rows:
        sorted_row = sorted(row, key=lambda item: _bbox_number(item.get("bbox"), "x_min"))
        layout_rows.append(
            {
                "text": " ".join(str(word.get("text") or "").strip() for word in sorted_row).strip(),
                "words": sorted_row,
                "bbox": _union_bboxes([word.get("bbox") for word in sorted_row]),
                "confidence": _word_confidence(sorted_row),
            }
        )
    layout_rows.sort(key=lambda row: (_bbox_number(row.get("bbox"), "y_min"), _bbox_number(row.get("bbox"), "x_min")))
    return layout_rows


def _layout_rows(page: dict[str, Any]) -> list[dict[str, Any]]:
    words = page.get("words")
    if isinstance(words, list) and words:
        return _layout_rows_from_words(words)

    lines = page.get("lines")
    if not isinstance(lines, list):
        return []
    rows = []
    for line in lines:
        if not isinstance(line, dict) or not str(line.get("text") or "").strip():
            continue
        line_words = line.get("words") if isinstance(line.get("words"), list) else []
        rows.append(
            {
                "text": str(line.get("text") or "").strip(),
                "words": line_words,
                "bbox": line.get("bbox"),
                "confidence": line.get("confidence") if line.get("confidence") is not None else _word_confidence(line_words),
            }
        )
    return rows


def _candidate_from_layout_row(row: dict[str, Any]) -> dict[str, Any] | None:
    row_words = row.get("words") if isinstance(row.get("words"), list) else []
    if not row_words:
        return None

    for index, word in enumerate(row_words):
        word_text = str(word.get("text") or "").strip()
        value_match = _VALUE_RE.search(word_text)
        if not value_match:
            continue

        test_name = _clean_test_name(" ".join(str(item.get("text") or "") for item in row_words[:index]))
        if len(test_name) < 2 or _VALUE_RE.search(test_name):
            continue

        value = _coerce_value(value_match.group("value"))
        if value is None:
            continue

        trailing_words = row_words[index:]
        context = str(row.get("text") or "").strip()
        value_bbox = word.get("bbox") if isinstance(word, dict) else None
        return {
            "test_name": test_name,
            "raw_value": value,
            "context": context,
            "value_start": context.find(value_match.group(0)),
            "value_end": context.find(value_match.group(0)) + len(value_match.group(0)),
            "unit_context": " ".join(str(item.get("text") or "") for item in trailing_words),
            "reference_context": " ".join(str(item.get("text") or "") for item in trailing_words),
            "method": "layout_row",
            "bbox": value_bbox or row.get("bbox"),
            "source_bbox": row.get("bbox"),
            "ocr_confidence": _word_confidence(trailing_words[:1]) or row.get("confidence"),
        }

    return None


def _coerce_pages(
    text: str,
    page_metadata: list[dict[str, Any]] | None,
    source_type: str,
    source_confidence: float | None,
) -> list[dict[str, Any]]:
    if page_metadata:
        pages = []
        for index, page in enumerate(page_metadata, start=1):
            page_text = str(page.get("text") or "").strip()
            if not page_text:
                continue
            pages.append(
                {
                    "page_number": int(page.get("page_number") or index),
                    "text": page_text,
                    "source_type": _normalize_source_type(page.get("source_type") or source_type),
                    "confidence": page.get("confidence", source_confidence),
                    "provider": page.get("provider"),
                    "width": page.get("width"),
                    "height": page.get("height"),
                    "words": page.get("words") if isinstance(page.get("words"), list) else [],
                    "lines": page.get("lines") if isinstance(page.get("lines"), list) else [],
                }
            )
        if pages:
            return pages

    pages_from_headers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in (text or "").splitlines():
        header = _PAGE_HEADER_RE.match(raw_line.strip())
        if header:
            if current and current["lines"]:
                current["text"] = "\n".join(current.pop("lines")).strip()
                pages_from_headers.append(current)
            current = {
                "page_number": int(header.group("page")),
                "source_type": _normalize_source_type(header.group("source")),
                "confidence": source_confidence,
                "lines": [],
            }
            continue
        if current is not None:
            current["lines"].append(raw_line)

    if current and current["lines"]:
        current["text"] = "\n".join(current.pop("lines")).strip()
        pages_from_headers.append(current)
    if pages_from_headers:
        return pages_from_headers

    return [
        {
            "page_number": 1,
            "text": text or "",
            "source_type": _normalize_source_type(source_type),
            "confidence": source_confidence,
        }
    ]


def _score_candidate(
    *,
    source_type: str,
    source_confidence: float | None,
    loinc_score: float,
    unit_detected: bool,
    reference_detected: bool,
    method: str,
) -> float:
    parsing_score = {
        "layout_row": 0.88,
        "structured_table": 0.82,
        "structured_line": 0.72,
    }.get(method, 0.65)
    parsing_score += 0.06 if unit_detected else -0.04
    parsing_score += 0.04 if reference_detected else 0.0
    parsing_score = max(0.0, min(1.0, parsing_score))

    ocr_score = 1.0 if source_type == "PDF" else source_confidence
    if ocr_score is None:
        ocr_score = 0.72 if source_type == "OCR" else 0.9
    ocr_score = max(0.0, min(1.0, float(ocr_score)))

    score = (ocr_score * 0.30) + (parsing_score * 0.35) + (loinc_score * 0.35)
    return round(max(0.0, min(0.99, score)), 3)


def _extract_page_candidates(page: dict[str, Any]) -> list[dict[str, Any]]:
    source_type = _normalize_source_type(page.get("source_type"))
    source_confidence = page.get("confidence")
    try:
        source_confidence = float(source_confidence) if source_confidence is not None else None
    except (TypeError, ValueError):
        source_confidence = None

    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for layout_row in _layout_rows(page):
        text = re.sub(r"\s+", " ", str(layout_row.get("text") or "")).strip()
        if not text or _line_looks_like_header(text):
            continue
        candidate = _candidate_from_layout_row(layout_row)
        if candidate:
            candidates.append(candidate)

    for line in (page.get("text") or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line or _line_looks_like_header(line):
            continue
        candidate = _candidate_from_columns(line) or _candidate_from_line(line)
        if candidate:
            candidates.append(candidate)

    for candidate in candidates:
        definition, loinc_score = map_loinc(candidate["test_name"])
        if definition is None:
            continue

        unit, unit_detected = _extract_unit(candidate["unit_context"], definition.unit)
        reference_range, reference_detected = _extract_reference(candidate["reference_context"], definition.reference_range)
        candidate_ocr_confidence = candidate.get("ocr_confidence")
        try:
            effective_source_confidence = float(candidate_ocr_confidence) if candidate_ocr_confidence is not None else source_confidence
        except (TypeError, ValueError):
            effective_source_confidence = source_confidence
        confidence_score = _score_candidate(
            source_type=source_type,
            source_confidence=effective_source_confidence,
            loinc_score=loinc_score,
            unit_detected=unit_detected,
            reference_detected=reference_detected,
            method=candidate["method"],
        )

        rows.append(
            {
                "key": definition.key,
                "name": definition.name,
                "test_name": definition.name,
                "loinc_code": definition.loinc_code,
                "category": definition.category,
                "unit": unit,
                "reference_range": reference_range,
                "raw_value": candidate["raw_value"],
                "confidence_score": confidence_score,
                "source_text": candidate["context"][:500],
                "source_span": candidate["context"][:500],
                "source_type": source_type,
                "page_number": page.get("page_number") or 1,
                "extraction_method": candidate["method"],
                "loinc_match_score": round(loinc_score, 3),
                "bbox": candidate.get("bbox"),
                "source_bbox": candidate.get("source_bbox"),
                "ocr_confidence": effective_source_confidence,
            }
        )

    return rows


def extract_lab_values(
    text: str,
    source_type: str = "PDF",
    source_confidence: float | None = None,
    page_metadata: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Parse report text into lab candidates using table and line structure."""
    pages = _coerce_pages(text, page_metadata, source_type, source_confidence)
    best_by_key: dict[str, dict[str, Any]] = {}

    for page in pages:
        for candidate in _extract_page_candidates(page):
            existing = best_by_key.get(candidate["key"])
            if existing is None or candidate["confidence_score"] > existing["confidence_score"]:
                best_by_key[candidate["key"]] = candidate

    return list(best_by_key.values())


def normalize_lab_values(raw_values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in raw_values:
        value = round(float(item["raw_value"]), 1)
        out.append(
            {
                "name": item["name"],
                "test_name": item.get("test_name") or item["name"],
                "loinc_code": item.get("loinc_code"),
                "category": item["category"],
                "unit": item["unit"],
                "reference_range": item["reference_range"],
                "value": value,
                "status": _classify_status(value, item["reference_range"]),
                "confidence_score": item.get("confidence_score", 0.0),
                "source_text": item.get("source_text") or item.get("source_span"),
                "source_span": item.get("source_span") or item.get("source_text"),
                "source_type": _normalize_source_type(item.get("source_type")),
                "page_number": item.get("page_number") or 1,
                "extraction_method": item.get("extraction_method", "structured_line"),
                "loinc_match_score": item.get("loinc_match_score"),
                "bbox": item.get("bbox"),
                "source_bbox": item.get("source_bbox"),
                "ocr_confidence": item.get("ocr_confidence"),
            }
        )
    return out


def store_lab_results(
    db: Session,
    user_id: UUID | str,
    report_id: UUID | str | None,
    normalized: list[dict[str, Any]],
) -> int:
    from sqlalchemy import bindparam, text as _text
    from sqlalchemy.dialects.postgresql import JSONB

    if not normalized:
        return 0

    now = datetime.now(timezone.utc)
    count = 0

    for item in normalized:
        values = {
            "user_id": str(user_id),
            "report_id": str(report_id) if report_id is not None else None,
            "name": item["name"],
            "loinc_code": item.get("loinc_code"),
            "value": item["value"],
            "unit": item["unit"],
            "reference_range": item["reference_range"],
            "category": item["category"],
            "status": item["status"],
            "confidence_score": item.get("confidence_score"),
            "source_text": item.get("source_text"),
            "source_span": item.get("source_span") or item.get("source_text"),
            "source_type": item.get("source_type", "PDF"),
            "page_number": item.get("page_number") or 1,
            "extraction_method": item.get("extraction_method", "structured_line"),
            "bbox": item.get("bbox"),
            "ts": now,
        }
        if report_id is not None:
            db.execute(
                _text(
                    """
                    INSERT INTO lab_results
                        (id, user_id, report_id, name, loinc_code, value, unit,
                         reference_range, category, status, confidence_score,
                         source_text, source_span, source_type, page_number,
                         extraction_method, bbox, timestamp, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, :report_id, :name, :loinc_code, :value, :unit,
                         :reference_range, :category, :status, :confidence_score,
                         :source_text, :source_span, :source_type, :page_number,
                         :extraction_method, :bbox, :ts, :ts, :ts)
                    ON CONFLICT (user_id, report_id, name)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        loinc_code = COALESCE(EXCLUDED.loinc_code, lab_results.loinc_code),
                        unit = EXCLUDED.unit,
                        reference_range = EXCLUDED.reference_range,
                        status = EXCLUDED.status,
                        confidence_score = EXCLUDED.confidence_score,
                        source_text = EXCLUDED.source_text,
                        source_span = EXCLUDED.source_span,
                        source_type = EXCLUDED.source_type,
                        page_number = EXCLUDED.page_number,
                        extraction_method = EXCLUDED.extraction_method,
                        bbox = EXCLUDED.bbox,
                        updated_at = EXCLUDED.updated_at
                    """
                ).bindparams(bindparam("bbox", type_=JSONB)),
                values,
            )
        else:
            db.execute(
                _text(
                    """
                    INSERT INTO lab_results
                        (id, user_id, report_id, name, loinc_code, value, unit,
                         reference_range, category, status, confidence_score,
                         source_text, source_span, source_type, page_number,
                         extraction_method, bbox, timestamp, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, NULL, :name, :loinc_code, :value, :unit,
                         :reference_range, :category, :status, :confidence_score,
                         :source_text, :source_span, :source_type, :page_number,
                         :extraction_method, :bbox, :ts, :ts, :ts)
                    """
                ).bindparams(bindparam("bbox", type_=JSONB)),
                values,
            )
        count += 1

    db.commit()
    return count


def _run_pipeline(
    text: str,
    user_id: UUID | str,
    report_id: UUID | str | None,
    db: Session,
    source_type: str = "PDF",
    source_confidence: float | None = None,
    page_metadata: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    log_pipeline("lab", step="extract_values", status="running", data="pending")
    try:
        raw = extract_lab_values(
            text,
            source_type=source_type,
            source_confidence=source_confidence,
            page_metadata=page_metadata,
        )
        if not raw:
            logger.info("lab_pipeline: no lab values found (report_id=%s)", report_id)
            log_pipeline("lab", step="extract_values", status="healthy", data="empty", extra=f"report_id={report_id}")
            return []

        log_pipeline("lab", step="normalize_values", status="running", data="pending")
        normalized = normalize_lab_values(raw)
        log_pipeline("lab", step="normalize_values", status="healthy", data=f"{len(normalized)}_markers")

        log_pipeline("lab", step="store_results", status="running", data="pending")
        count = store_lab_results(db, user_id, report_id, normalized)
        abnormal_rows = [
            item for item in normalized
            if str(item.get("status") or "").strip().lower() in {"high", "low", "abnormal", "critical"}
        ]
        if abnormal_rows:
            try:
                from services.event_service import emit_event

                emit_event(
                    "LAB_RESULT_ABNORMAL",
                    user_id,
                    {
                        "report_id": str(report_id) if report_id is not None else None,
                        "abnormal_count": len(abnormal_rows),
                        "abnormal_names": [item.get("name") for item in abnormal_rows if item.get("name")],
                    },
                )
            except Exception:
                logger.exception("lab_pipeline: failed to emit abnormal lab notification event")
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is not None:
                from ai.scoring.realtime.event_listener import ScoringEventListener

                ScoringEventListener.on_lab_upload(db, user)
        except Exception:
            logger.exception("lab_pipeline: scoring refresh failed for user=%s report=%s", user_id, report_id)
        logger.info("lab_pipeline: stored %d results (user=%s report=%s)", count, user_id, report_id)
        log_pipeline("lab", step="complete", status="healthy", data="fetched", extra=f"stored={count}")
        return normalized
    except Exception:
        logger.exception("lab_pipeline: failed for user=%s report=%s", user_id, report_id)
        log_pipeline("lab", step="run_lab_pipeline", status="unhealthy", data="failed")
        return []


def _resolve_report(db: Session, report_id: UUID | str) -> Report | None:
    try:
        report_uuid = report_id if isinstance(report_id, UUID) else UUID(str(report_id))
    except (TypeError, ValueError):
        logger.warning("lab_pipeline: invalid report id %s", report_id)
        return None

    return db.query(Report).filter(Report.id == report_uuid, Report.is_deleted == False).first()


def _text_provenance(summary_data: Any) -> tuple[str, float | None, list[dict[str, Any]] | None]:
    if not isinstance(summary_data, dict):
        return "PDF", None, None

    pages = summary_data.get("text_pages")
    if not isinstance(pages, list):
        layout = summary_data.get("ocr_layout")
        pages = layout.get("pages") if isinstance(layout, dict) else None
    page_metadata = pages if isinstance(pages, list) else None
    source_type = _normalize_source_type(summary_data.get("text_source") or "PDF")
    if page_metadata and any(_normalize_source_type(page.get("source_type")) == "OCR" for page in page_metadata if isinstance(page, dict)):
        source_type = "OCR"

    raw_confidence = summary_data.get("ocr_confidence")
    try:
        confidence = float(raw_confidence) if raw_confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    return source_type, confidence, page_metadata


def run_lab_pipeline(
    report_id: UUID | str | None,
    text: str | None = None,
    user_id: UUID | str | None = None,
    db: Session | None = None,
    source_type: str = "PDF",
    source_confidence: float | None = None,
    page_metadata: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Full pipeline entrypoint."""
    owns_session = db is None
    session = db or SessionLocal()

    try:
        resolved_report_id = report_id
        resolved_text = (text or "").strip()
        resolved_user_id = user_id
        resolved_source_type = _normalize_source_type(source_type)
        resolved_source_confidence = source_confidence
        resolved_page_metadata = page_metadata

        if resolved_user_id is None or not resolved_text:
            if report_id is None:
                logger.warning("lab_pipeline: report_id is required when text/user context is missing")
                return []

            report = _resolve_report(session, report_id)
            if report is None:
                logger.warning("lab_pipeline: report %s not found", report_id)
                return []

            resolved_report_id = report.id
            resolved_user_id = report.user_id
            resolved_text = (report.parsed_text or "").strip()
            resolved_source_type, resolved_source_confidence, resolved_page_metadata = _text_provenance(report.summary_data)

            if not resolved_text and isinstance(report.summary_data, dict):
                resolved_text = str(report.summary_data.get("full_text") or "").strip()

            if not resolved_text:
                logger.info("lab_pipeline: report %s has no extracted text yet", report_id)
                log_pipeline("lab", step="load_report", status="healthy", data="empty", extra=f"report_id={report_id}")
                return []

        pipeline_kwargs: dict[str, Any] = {}
        if resolved_source_type != "PDF":
            pipeline_kwargs["source_type"] = resolved_source_type
        if resolved_source_confidence is not None:
            pipeline_kwargs["source_confidence"] = resolved_source_confidence
        if resolved_page_metadata:
            pipeline_kwargs["page_metadata"] = resolved_page_metadata

        return _run_pipeline(resolved_text, resolved_user_id, resolved_report_id, session, **pipeline_kwargs)
    finally:
        if owns_session:
            session.close()
