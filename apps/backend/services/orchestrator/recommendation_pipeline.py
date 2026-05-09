from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.recommendation_engine import generate_recommendation_plan, generate_recommendation_plans
from services.recommendation_service import generate_test_recommendations


class RecommendationPipeline:
    def generate_plan(self, user_id: str, *, db: Session) -> dict[str, Any]:
        return generate_recommendation_plan(user_id, db=db)

    def generate_plans(self, user_id: str, *, db: Session) -> list[dict[str, Any]]:
        return generate_recommendation_plans(user_id, db=db)

    def generate_tests(self, user_id: str, *, db: Session) -> list[dict[str, Any]]:
        return generate_test_recommendations(user_id, db=db)
