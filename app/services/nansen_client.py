import asyncio
import httpx
from app.core.config import settings
from app.models.nansen import NansenResponse, SmartMoneyHolding, DexTrade
from app.core.utils import retry_async
from loguru import logger
from typing import List, Dict, Any

class NansenClient:
    def __init__(self) -> None:
        self.base_url = settings.NANSEN_BASE_URL
        self.headers = {
            "apikey": settings.NANSEN_API_KEY.get_secret_value(),
            "Content-Type": "application/json",
        }

        # Lista de redes prioritarias según Vicente
        self.supported_chains = ["ethereum", "base", "arbitrum", "avalanche", "solana", "bsc"]
        
    @retry_async()
    async def get_smart_money_flows(
        self,
        chain: str,
        smart_money_labels: List[str] = ["Smart Trader", "Fund", "30D Smart Trader"],
    ) -> NansenResponse:
        """
        Obtiene Netflows con foco en etiquetas de alta convicción (Smart Money Real).
        """
        if chain not in self.supported_chains:
            logger.warning(f"[Nansen] Red {chain} no testada oficialmente. Procediendo con cautela.")
        
        url = f"{self.base_url}/smart-money/netflow"
        payload: dict = {
            "chains": [chain],
            "filters": {
                "include_smart_money_labels": smart_money_labels
            }
        }
        
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
        
        data = response.json()
        result = NansenResponse(**data)
        
        # Log simplificado: Vicente no quiere ver decimales.
        logger.info(f"[Nansen] {chain.upper()}: Detectados {len(result.data)} tokens con flujo SM.")
        return result

    @retry_async()
    async def get_top_signals(self, chain: str) -> List[Dict[str, Any]]:
        """
        Método de conveniencia para Gemini 1.5 Pro.
        Cruza Holdings + DEX Trades para identificar la 'Caza de Lanzamientos'.
        """
        logger.info(f"[Nansen] Generando señales combinadas para {chain}...")
        
        # Ejecución en paralelo para ganar velocidad
        holdings_task = self.get_smart_money_holdings(chain)
        trades_task = self.get_dex_trades(chain)
        
        holdings, trades = await asyncio.gather(holdings_task, trades_task)

        # Lógica de filtrado: Tokens que aparecen en trades recientes 
        # Y que además están en el TOP de holdings.
        signals = []
        trading_tokens = {t.token_symbol for t in trades}
        
        for h in holdings:
            if h.token_symbol in trading_tokens:
                signals.append({
                    "symbol": h.token_symbol,
                    "address": h.token_address,
                    "sm_count": h.smart_money_wallet_count,
                    "change_pct": h.change_7d # O la métrica de cambio disponible
                })

        return signals[:10] # Retornamos solo el TOP 10 para no saturar el análisis

    @retry_async()
    async def get_smart_money_holdings(self, chain: str) -> List[SmartMoneyHolding]:
        url = f"{self.base_url}/smart-money/holdings"
        payload = {"chains": [chain]}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            raw = response.json().get("data", [])
            return [SmartMoneyHolding(**item) for item in raw]

    @retry_async()
    async def get_dex_trades(self, chain: str) -> List[DexTrade]:
        url = f"{self.base_url}/smart-money/dex-trades"
        payload = {"chains": [chain]}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            raw = response.json().get("data", [])
            return [DexTrade(**item) for item in raw]
