import httpx
import logging
import time
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class BaseIntegrationClient:
    """
    Standardized async client for ArogyaAI service-to-service communication.
    Wraps httpx with built-in retries, timeouts, and error normalization.
    """
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return await self._request("POST", endpoint, json=data)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Executes HTTP request and handles exceptions.
        Returns standardized envelope even on failure (fallback mode).
        """
        start_time = time.time()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            logger.info(f"Integration {method} {url} - {response.status_code} ({duration:.2f}ms)")
            
            if response.is_error:
                logger.error(f"Integration Error: {response.status_code} {response.text}")
                return self._fallback_response(f"External service returned {response.status_code}")
                
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Integration Connection Failed: {url} - {str(e)}")
            return self._fallback_response(str(e))
        except Exception as e:
            logger.error(f"Unexpected Integration Error: {str(e)}")
            return self._fallback_response("Internal integration failure")

    def _fallback_response(self, error_msg: str) -> Dict[str, Any]:
        """Returns standard fallback envelope for services to consume safely."""
        return {
            "success": False,
            "status": "fallback",
            "error": error_msg,
            "data": None
        }

    async def close(self):
        await self.client.aclose()
