from integrations.base_client import BaseIntegrationClient
from typing import Dict, Any, Optional
import os

class RAGClient(BaseIntegrationClient):
    """
    Client for the RAG (Retrieval-Augmented Generation) Microservice.
    Provides medical context and AI-driven explanations for predictions.
    """
    def __init__(self):
        base_url = os.getenv("RAG_SERVICE_URL", "http://rag-service:8000")
        super().__init__(base_url=base_url)

    async def get_explanation(self, prediction_id: str) -> Dict[str, Any]:
        """Fetch detailed AI explanation for a specific prediction."""
        return await self.post("/explain", data={"prediction_id": prediction_id})
