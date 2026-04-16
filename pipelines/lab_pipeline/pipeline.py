"""
Lab pipeline — processes raw lab report text into structured, persisted lab results.

Pure functions with a single side effect: DB write in store_lab_results().

Entry point: run_lab_pipeline(text, user_id, report_id, db)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models import User
from pipelines.storage_pipeline.service import StoragePipelineService

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Reference catalogue — single source of truth for all known lab parameters
# ---------------------------------------------------------------------------
_LAB_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "hemoglobin",
        "name": "Hemoglobin",
        "category": "hematology",
        "unit": "g/dL",
        "reference_range": "13.5 - 17.5",
        "patterns": [r"hemoglobin(?:\s*\(hb\))?[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "wbc",
        "name": "WBC",
        "category": "hematology",
        "unit": "x10^3/uL",
        "reference_range": "4.0 - 11.0",
        "patterns": [r"(?:wbc|white blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "rbc",
        "name": "RBC",
        "category": "hematology",
        "unit": "x10^6/uL",
        "reference_range": "4.5 - 5.9",
        "patterns": [r"(?:rbc|red blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "platelets",
        "name": "Platelets",
        "category": "hematology",
        "unit": "x10^3/uL",
        "reference_range": "150 - 450",
        "patterns": [r"(?:platelets?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "glucose",
        "name": "Glucose (Fasting)",
        "category": "metabolic",
        "unit": "mg/dL",
        "reference_range": "70 - 99",
        "patterns": [
            r"(?:fasting glucose|glucose \(fasting\)|blood glucose|glucose)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"
        ],
    },
    {
        "key": "hba1c",
        "name": "HbA1c",
        "category": "metabolic",
        "unit": "%",
        "reference_range": "< 5.7",
        "patterns": [r"(?:hba1c|a1c)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "creatinine",
        "name": "Creatinine",
        "category": "biochemistry",
        "unit": "mg/dL",
        "reference_range": "0.7 - 1.3",
        "patterns": [r"(?:creatinine)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "urea",
        "name": "Urea",
        "category": "biochemistry",
        "unit": "mg/dL",
        "reference_range": "7 - 20",
        "patterns": [r"(?:urea|blood urea)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "ldl",
        "name": "LDL Cholesterol",
        "category": "lipid",
        "unit": "mg/dL",
        "reference_range": "< 100",
        "patterns": [
            r"(?:ldl(?: cholesterol)?|low-density lipoprotein(?: cholesterol)?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"
        ],
    },
    {
        "key": "hdl",
        "name": "HDL Cholesterol",
        "category": "lipid",
        "unit": "mg/dL",
        "reference_range": "> 40",
        "patterns": [
            r"(?:hdl(?: cholesterol)?|high-density lipoprotein(?: cholesterol)?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"
        ],
    },
    {
        "key": "triglycerides",
        "name": "Triglycerides",
        "category": "lipid",
        "unit": "mg/dL",
        "reference_range": "< 150",
        "patterns": [r"(?:triglycerides?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "tsh",
        "name": "TSH",
        "category": "thyroid",
        "unit": "uIU/mL",
        "reference_range": "0.4 - 4.0",
        "patterns": [r"(?:tsh)[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
]


# ---------------------------------------------------------------------------
# Pure helper: classify status from reference range string
# ---------------------------------------------------------------------------
def _classify_status(value: float, reference_range: str) -> str:
    normalized = (reference_range or "").strip()

    lt_match = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if lt_match:
        threshold = float(lt_match.group(1))
        if value <= threshold:
            return "normal"
        return "borderline" if value <= threshold * 1.15 else "high"

    gt_match = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if gt_match:
        threshold = float(gt_match.group(1))
        if value >= threshold:
            return "normal"
        return "borderline" if value >= threshold * 0.85 else "low"

    range_match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        if low <= value <= high:
            return "normal"
        band = max((high - low) * 0.1, 0.1)
        if value < low:
            return "borderline" if value >= low - band else "low"
        return "borderline" if value <= high + band else "high"

    return "normal"


# ---------------------------------------------------------------------------
# Step 1: Extract raw numeric matches from text (no side effects)
# ---------------------------------------------------------------------------
def extract_lab_values(text: str) -> list[dict[str, Any]]:
    """
    Regex-scan *text* against all known lab parameter patterns.

    Returns a list of dicts with keys:
        key, name, category, unit, reference_range, raw_value
    """
    results: list[dict[str, Any]] = []

    for defn in _LAB_DEFINITIONS:
        raw: float | None = None
        for pattern in defn["patterns"]:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    raw = float(match.group(1))
                    break
                except (TypeError, ValueError):
                    continue

        if raw is not None:
            results.append(
                {
                    "key": defn["key"],
                    "name": defn["name"],
                    "category": defn["category"],
                    "unit": defn["unit"],
                    "reference_range": defn["reference_range"],
                    "raw_value": raw,
                }
            )

    return results


# ---------------------------------------------------------------------------
# Step 2: Normalise raw extractions into canonical format (no side effects)
# ---------------------------------------------------------------------------
def normalize_lab_values(raw_values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Apply rounding + status classification to each extraction.

    Returns list of dicts matching the canonical format:
        name, value, unit, reference_range, category, status
    """
    normalized: list[dict[str, Any]] = []

    for item in raw_values:
        value = round(item["raw_value"], 1)
        normalized.append(
            {
                "name": item["name"],
                "category": item["category"],
                "unit": item["unit"],
                "reference_range": item["reference_range"],
                "value": value,
                "status": _classify_status(value, item["reference_range"]),
            }
        )

    return normalized


# ---------------------------------------------------------------------------
# Step 3: Persist to DB (upsert on user_id + report_id + name)
# ---------------------------------------------------------------------------
def store_lab_results(
    db: Session,
    user_id: UUID | str,
    report_id: UUID | str | None,
    normalized_values: list[dict[str, Any]],
) -> int:
    """
    Upsert *normalized_values* into the lab_results table.

    Uses a raw SQL upsert (ON CONFLICT DO UPDATE) so that re-processing the
    same report is idempotent.  Returns the number of rows affected.
    """
    from sqlalchemy import text as _text

    if not normalized_values:
        return 0

    rows_affected = 0
    now = datetime.now(timezone.utc)

    for item in normalized_values:
        if report_id is not None:
            # Upsert keyed on (user_id, report_id, name)
            db.execute(
                _text(
                    """
                    INSERT INTO lab_results
                        (id, user_id, report_id, name, value, unit,
                         reference_range, category, status, timestamp,
                         created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, :report_id, :name, :value, :unit,
                         :reference_range, :category, :status, :ts, :ts, :ts)
                    ON CONFLICT (user_id, report_id, name)
                    DO UPDATE SET
                        value           = EXCLUDED.value,
                        status          = EXCLUDED.status,
                        updated_at      = EXCLUDED.updated_at
                    """
                ),
                {
                    "user_id": str(user_id),
                    "report_id": str(report_id),
                    "name": item["name"],
                    "value": item["value"],
                    "unit": item["unit"],
                    "reference_range": item["reference_range"],
                    "category": item["category"],
                    "status": item["status"],
                    "ts": now,
                },
            )
        else:
            # No report_id — simple insert
            db.execute(
                _text(
                    """
                    INSERT INTO lab_results
                        (id, user_id, report_id, name, value, unit,
                         reference_range, category, status, timestamp,
                         created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :user_id, NULL, :name, :value, :unit,
                         :reference_range, :category, :status, :ts, :ts, :ts)
                    """
                ),
                {
                    "user_id": str(user_id),
                    "name": item["name"],
                    "value": item["value"],
                    "unit": item["unit"],
                    "reference_range": item["reference_range"],
                    "category": item["category"],
                    "status": item["status"],
                    "ts": now,
                },
            )

        rows_affected += 1

    db.commit()
    return rows_affected


# ---------------------------------------------------------------------------
# Orchestrator: extract → normalize → store
# ---------------------------------------------------------------------------
def run_lab_pipeline(
    text: str,
    user_id: UUID | str,
    report_id: UUID | str | None,
    db: Session,
) -> list[dict[str, Any]]:
    """
    Full pipeline: parse text → classify → persist → return normalized values.

    Never raises — failures are logged and an empty list is returned so the
    caller (upload flow) continues normally.
    """
    try:
        raw = extract_lab_values(text)
        if not raw:
            logger.info("Lab pipeline: no recognisable lab values in text (report_id=%s)", report_id)
            return []

        normalized = normalize_lab_values(raw)
        count = store_lab_results(db, user_id, report_id, normalized)
        user = db.query(User).filter(User.id == user_id).first()
        if user is not None:
            try:
                StoragePipelineService.store_lab_values(db, user, normalized, report_id=report_id)
            except Exception:
                logger.exception("Lab pipeline: lab_values persistence failed for user=%s report=%s", user_id, report_id)
        logger.info(
            "Lab pipeline: stored %d lab results for user=%s report=%s",
            count,
            user_id,
            report_id,
        )
        return normalized

    except Exception:
        logger.exception(
            "Lab pipeline failed for user=%s report=%s — results not persisted",
            user_id,
            report_id,
        )
        return []
