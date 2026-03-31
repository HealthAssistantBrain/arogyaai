from integrations.base_client import BaseIntegrationClient
from typing import Dict, Any, Optional
import os

class WearableClient(BaseIntegrationClient):
    """
    Client for the Wearable/IoT Data Microservice.
    Handles syncing heart rate, sleep, and step data from third-party devices.
    """
    def __init__(self):
        base_url = os.getenv("WEARABLE_SERVICE_URL", "http://wearable-service:8003")
        super().__init__(base_url=base_url)

    async def sync_user_data(self, user_id: str) -> Dict[str, Any]:
        """Trigger a background sync for user wearable data."""
        return await self.post(f"/sync/{user_id}")

    async def get_vitals(self, user_id: str) -> Dict[str, Any]:
        """Fetch processed vitals (HRV, Sleep, Steps) from the pipeline."""
        return await self.get(f"/vitals/{user_id}")
