"""
Lab pipeline service — processes raw lab report text into structured DB records.

Lives inside apps/backend/services/ so it is available inside the Docker container
without requiring the monorepo pipelines/ directory (which is not COPYed into the image).

Entry point: run_lab_pipeline(text, user_id, report_id, db)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Lab parameter catalogue (single source of truth shared with the route)
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
        "patterns": [r"creatinine[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
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
        "patterns": [r"triglycerides?[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
    {
        "key": "tsh",
        "name": "TSH",
        "category": "thyroid",
        "unit": "uIU/mL",
        "reference_range": "0.4 - 4.0",
        "patterns": [r"tsh[:\s\-]*([0-9]+(?:\.[0-9]+)?)"],
    },
]


def _classify_status(value: float, reference_range: str) -> str:
    normalized = (reference_range or "").strip()

    lt = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if lt:
        t = float(lt.group(1))
        if value <= t:
            return "normal"
        return "borderline" if value <= t * 1.15 else "high"

    gt = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if gt:
        t = float(gt.group(1))
        if value >= t:
            return "normal"
        return "borderline" if value >= t * 0.85 else "low"

    rng = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if rng:
        lo, hi = float(rng.group(1)), float(rng.group(2))
        if lo <= value <= hi:
            return "normal"
        band = max((hi - lo) * 0.1, 0.1)
        if value < lo:
            return "borderline" if value >= lo - band else "low"
        return "borderline" if value <= hi + band else "high"

    return "normal"


def extract_lab_values(text: str) -> list[dict[str, Any]]:
    """Parse text and return matched lab parameter dicts (no side-effects)."""
    results: list[dict[str, Any]] = []
    for defn in _LAB_DEFINITIONS:
        raw: float | None = None
        for pattern in defn["patterns"]:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                try:
                    raw = float(m.group(1))
                    break
                except (TypeError, ValueError):
                    continue
        if raw is not None:
            results.append({**defn, "raw_value": raw})
    return results


def normalize_lab_values(raw_values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round values and classify status (no side-effects)."""
    out = []
    for item in raw_values:
        value = round(item["raw_value"], 1)
        out.append(
            {
                "name": item["name"],
                "category": item["category"],
                "unit": item["unit"],
                "reference_range": item["reference_range"],
                "value": value,
                "status": _classify_status(value, item["reference_range"]),
            }
        )
    return out


def store_lab_results(
    db: Session,
    user_id: UUID | str,
    report_id: UUID | str | None,
    normalized: list[dict[str, Any]],
) -> int:
    """Upsert normalized lab rows into lab_results table. Returns count stored."""
    from sqlalchemy import text as _text

    if not normalized:
        return 0

    now = datetime.now(timezone.utc)
    count = 0

    for item in normalized:
        if report_id is not None:
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
                        value      = EXCLUDED.value,
                        status     = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
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
        count += 1

    db.commit()
    return count


def run_lab_pipeline(
    text: str,
    user_id: UUID | str,
    report_id: UUID | str | None,
    db: Session,
) -> list[dict[str, Any]]:
    """
    Full pipeline: extract → normalize → persist.
    Never raises — failures are logged and [] is returned.
    """
    try:
        raw = extract_lab_values(text)
        if not raw:
            logger.info("lab_pipeline: no lab values found (report_id=%s)", report_id)
            return []
        normalized = normalize_lab_values(raw)
        count = store_lab_results(db, user_id, report_id, normalized)
        logger.info("lab_pipeline: stored %d results (user=%s report=%s)", count, user_id, report_id)
        return normalized
    except Exception:
        logger.exception("lab_pipeline: failed for user=%s report=%s", user_id, report_id)
        return []
