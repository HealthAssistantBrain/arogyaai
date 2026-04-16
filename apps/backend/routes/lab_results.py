from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from models.lab_result import LabResult
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/lab-results", tags=["Lab Results"])

# ---------------------------------------------------------------------------
# Allowed category values (must match frontend FILTERS exactly)
# ---------------------------------------------------------------------------
_VALID_CATEGORIES = {"hematology", "biochemistry", "metabolic", "lipid", "thyroid"}


# ---------------------------------------------------------------------------
# Status classifier — kept here so the route is self-contained if the pipeline
# hasn't been run yet (shouldn't happen in production, but guards edge cases).
# ---------------------------------------------------------------------------
def _classify_status(value: float, reference_range: str) -> str:
    normalized = (reference_range or "").strip()

    less_than_match = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if less_than_match:
        threshold = float(less_than_match.group(1))
        if value <= threshold:
            return "normal"
        if value <= threshold * 1.15:
            return "borderline"
        return "high"

    greater_than_match = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", normalized)
    if greater_than_match:
        threshold = float(greater_than_match.group(1))
        if value >= threshold:
            return "normal"
        if value >= threshold * 0.85:
            return "borderline"
        return "low"

    range_match = re.match(
        r"^([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)$",
        normalized,
    )
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
# GET /api/v1/lab-results
# ---------------------------------------------------------------------------
@router.get("")
def get_lab_results(
    category: str | None = Query(None, description="Filter by category (hematology, biochemistry, etc.)"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Return the latest lab result for each tracked parameter for the current user.
    Also attaches the last 6 measured values as `trend`.

    Data is sourced from the `lab_results` table populated by the lab pipeline
    at report-upload time. Returns empty state if no data has been processed yet.
    """
    # Build query — always filter by user, optionally by category
    query = db.query(LabResult).filter(LabResult.user_id == current_user.id)

    if category:
        normalised_cat = category.strip().lower()
        if normalised_cat in _VALID_CATEGORIES:
            query = query.filter(LabResult.category == normalised_cat)

    # Fetch all rows ordered oldest-first so trend lists are chronological
    try:
        rows: list[LabResult] = query.order_by(LabResult.timestamp.asc()).all()
    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "source": "db",
            "error": str(e),
            "data": [],
            "last_updated": None
        }

    if not rows:
        return {
            "success": True,
            "status": "empty",
            "source": "db",
            "error": None,
            "data": [],
            "last_updated": None
        }

    # Group by parameter name; collect all values in chronological order
    history: dict[str, list[LabResult]] = defaultdict(list)
    for row in rows:
        if row.name:
            history[row.name].append(row)

    lab_results: list[dict[str, Any]] = []
    latest_timestamp = None

    for name, records in history.items():
        # trend = last 6 measured values (chronologically, oldest → newest)
        trend_records = records[-6:]
        trend = [round(r.value, 1) for r in trend_records]
        latest = records[-1]
        
        if not latest_timestamp or (latest.timestamp and latest.timestamp > latest_timestamp):
            latest_timestamp = latest.timestamp

        lab_results.append(
            {
                "name": latest.name,
                "value": round(latest.value, 1),
                "unit": latest.unit or "",
                "reference_range": latest.reference_range or "",
                "status": latest.status or _classify_status(latest.value, latest.reference_range or ""),
                "category": latest.category or "other",
                "trend": trend,
            }
        )

    return {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": lab_results,
        "last_updated": latest_timestamp.isoformat() if latest_timestamp else None
    }
