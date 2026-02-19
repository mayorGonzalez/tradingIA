import httpx
from app.core.config import settings
from app.models.nansen import NansenResponse

class NansenClient:
    def __init__(self) -> None:
        self.headers = {
            "apikey": settings.NANSEN_API_KEY.get_secret_value(),
            "Content-Type": "application/json",
        }

    async def get_smart_money_flows(self, chain: str = "ethereum") -> NansenResponse:
        """Obtiene el flujo de smart money para un token"""

        url = f"{settings.NANSEN_BASE_URL}/smart-money-flow/netflows"
        payload = {
            "chains": [chain],
            "time_range": "24h"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload
            )
        response.raise_for_status()
        return NansenResponse(**response.json())