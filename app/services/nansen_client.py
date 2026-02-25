import asyncio
import httpx
from app.core.config import settings
from app.models.nansen import NansenResponse, SmartMoneyHolding, DexTrade
from app.core.utils import retry_async
from loguru import logger
from typing import List

class NansenClient:
    def __init__(self) -> None:
        self.base_url = settings.NANSEN_BASE_URL
        self.headers = {
            "apikey": settings.NANSEN_API_KEY.get_secret_value(),
            "Content-Type": "application/json",
        }

    @retry_async()
    async def get_smart_money_flows(
        self,
        chain: str = "ethereum",
        smart_money_labels: List[str] | None = None,
    ) -> NansenResponse:
        """Obtiene los netflows de Smart Money. 
        
        Filtra opcionalmente por tipo de wallet: Fund, Smart Trader, 30D Smart Trader, etc.
        """
        url = f"{self.base_url}/smart-money/netflow"
        payload: dict = {"chains": [chain]}
        
        # Concentración: filtrar por etiquetas premium si se especifican
        if smart_money_labels:
            payload["filters"] = {
                "include_smart_money_labels": smart_money_labels
            }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        await asyncio.sleep(0.5)  # Rate-limit cortesía
        result = NansenResponse(**response.json())
        logger.info(f"[Nansen] Netflow: {len(result.data)} tokens (chain={chain})")
        return result

    @retry_async()
    async def get_smart_money_holdings(
        self,
        chain: str = "ethereum",
    ) -> List[SmartMoneyHolding]:
        """Obtiene qué tokens están ACUMULANDO las wallets de Smart Money.
        
        Clave para confirmar que el inflow no es puntual, sino que hay posiciones sostenidas.
        """
        url = f"{self.base_url}/smart-money/holdings"
        payload = {"chains": [chain]}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        await asyncio.sleep(0.5)
        raw = response.json().get("data", [])
        holdings = [SmartMoneyHolding(**item) for item in raw]
        logger.info(f"[Nansen] Holdings: {len(holdings)} tokens en cartera Smart Money")
        return holdings

    @retry_async()
    async def get_dex_trades(
        self,
        chain: str = "ethereum",
    ) -> List[DexTrade]:
        """Obtiene las operaciones en DEX recientes de Smart Money.
        
        Permite detectar tokens que están siendo comprados activamente ahora mismo,
        incluso si el netflow acumulado aún no es grande.
        """
        url = f"{self.base_url}/smart-money/dex-trades"
        payload = {"chains": [chain]}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        await asyncio.sleep(0.5)
        raw = response.json().get("data", [])
        trades = [DexTrade(**item) for item in raw]
        logger.info(f"[Nansen] DEX Trades: {len(trades)} operaciones recientes")
        return trades
