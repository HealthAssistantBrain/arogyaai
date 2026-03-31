from integrations.base_client import BaseIntegrationClient
from typing import Dict, Any, Optional
import os

class PredictionClient(BaseIntegrationClient):
    """
    Client for the ML Prediction Microservice.
    Handles risk scores, disease projections, and biological age calculations.
    """
    def __init__(self):
        base_url = os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8001")
        super().__init__(base_url=base_url)

    async def get_prediction(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch latest health risk prediction from ML pipeline."""
        return await self.post("/predict", data=user_data)

    async def get_trajectory(self, user_id: str) -> Dict[str, Any]:
        """Fetch multi-year health trajectory data."""
        return await self.get(f"/projections/{user_id}")
