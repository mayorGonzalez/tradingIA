"""
SignalEngine — Motor de Scoring Multidimensional
=================================================
Cruza datos de tres fuentes de Nansen para reducir falsos positivos:

  Dimensión 1 (Netflow)    → ¿Hay entrada neta de dinero en las últimas 24h?
  Dimensión 2 (Holdings)   → ¿Smart Money ya lo tiene en cartera? (tesis sostenida)
  Dimensión 3 (DEX Trades) → ¿Se está comprando activamente ahora mismo en DEX?

Cada dimensión aporta una puntuación parcial ponderada. Solo pasan al ExchangeClient
los tokens con score preliminar >= 50 (evitar llamadas API innecesarias).
"""

import pandas as pd
import asyncio
from typing import List, Dict, Set
from loguru import logger
from collections import Counter

from app.core.config import settings
from app.models.nansen import SmartMoneyFlow, SmartMoneyHolding, DexTrade, SignalResult
from app.infraestructure.exchange_client import ExchangeClient
from app.services.portfolio_service import PortfolioService


class SignalEngine:
    def __init__(
        self,
        exchange_client,
        portfolio_service,
        min_inflow_usd: float = 1000):
        self.exchange = exchange_client
        self.portfolio = portfolio_service
        self.min_inflow_usd = min_inflow_usd
        self._exchange_semaphore = asyncio.Semaphore(5)

    async def analyze_flows(
        self,
        flows,
        holdings = None,
        dex_trades = None,
    ) -> List[SignalResult]:
        """
        Analiza flujos de Smart Money con scoring multidimensional.

        Args:
            flows:      Datos del endpoint /smart-money/netflow
            holdings:   Datos de /smart-money/holdings (tokens acumulados)
            dex_trades: Datos de /smart-money/dex-trades (compras recientes en DEX)
        """
        if not flows:
            logger.warning("No se recibieron flujos para analizar.")
            return []

        # --- Preprocesar datos de enriquecimiento ---
        # Conjunto de símbolos que Smart Money ya tiene en cartera
        held_symbols: Set[str] = {h.token_symbol for h in (holdings or [])}
        
        # Conteo de cuántas veces aparece cada token como BUY en DEX trades
        dex_buy_counts: Counter[str] = Counter()
        for trade in (dex_trades or []):
            # Si el token se COMPRÓ (no se vendió) contamos +1
            if trade.token_sold_symbol in ("ETH", "USDT", "USDC", "WETH", "SOL", "BNB"):
                dex_buy_counts[trade.token_bought_address] += 1

        # --- Filtro inicial por inflow mínimo ---
        df = pd.DataFrame([f.model_dump() for f in flows])
        df = df[df['net_flow_usd'] >= self.min_inflow_usd].copy()

        if df.empty:
            logger.info(f"Sin señales que superen el umbral de ${self.min_inflow_usd:,.0f}.")
            return []

        logger.info(f"Evaluando {len(df)} tokens con inflow > ${self.min_inflow_usd:,.0f}...")

        # Lanzar validaciones en paralelo (sin bloquear unas con otras)
        tasks = [
            self._validate_signal(row, held_symbols, dex_buy_counts)
            for _, row in df.iterrows()
        ]
        validated = await asyncio.gather(*tasks)

        results = [r for r in validated if r is not None]
        
        # Ordenar por score descendente
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results

    async def _validate_signal(
        self,
        row: pd.Series,
        held_addresses: Set[str],
        dex_buy_counts: Counter,
    ) -> SignalResult | None:
        """Calcula el score 0-100 y valida técnicamente un token candidato."""
        address = row['token_address']
        symbol = row['token_symbol']
        net_flow_24h = float(row['net_flow_usd'])
        

        # =====================================================================
        # DIMENSIÓN 1 — VOLUMEN NETO (peso: SCORE_WEIGHT_FLOW = 40%)
        # Puntuación proporcional al inflow detectado.
        # Se normaliza contra 10x el umbral mínimo para llegar a 100pts.
        # =====================================================================
        # 1. Flujo (40%): Bonus por consistencia 7d
        vol_score = min((net_flow_24h / (self.min_inflow_usd * 5)) * 100, 100)
        if float(row.get('net_flow_7d_usd', 0)) > net_flow_24h:
            vol_score = min(vol_score * 1.2, 100)

        # 2. Concentración (30%): ¿Es una apuesta institucional?
        conc_score = 0.0
        if address in held_addresses:
            conc_score += 70  # Ya está en carteras SM: Confianza extrema
        
        traders = int(row.get('trader_count', 0))
        conc_score = min(conc_score + (traders * 5), 100) # 6+ traders añaden el resto

        # 3. Persistencia (30%): ¿Compran ahora mismo?
        buys = dex_buy_counts.get(address, 0)
        dex_score = min(buys * 20, 100) # 5 compras = 100pts
        
        if await self.portfolio.check_persistence(symbol):
            dex_score = min(dex_score + 25, 100)

        total_score = (
            vol_score * 0.4 + 
            conc_score * 0.3 + 
            dex_score * 0.3
        )

        if total_score < settings.MIN_SCORE_THRESHOLD:
            return None

        # --- VALIDACIÓN TÉCNICA (Con protección de Rate-Limit) ---
        async with self._exchange_semaphore:
            try:
                # Obtenemos datos de precio y volumen para evitar 'Pumps'
                change_1h = await self.exchange.get_price_change_1h(symbol)
                # Si ha subido demasiado, marcamos factor de riesgo
                risks = []
                if change_1h and change_1h > settings.MAX_PRICE_CHANGE_1H_PCT:
                    risks.append("FOMO_ZONE")
                
                # Token joven (Punto 9: Lanzamientos)
                age = int(row.get('token_age_days') or 0)
                if 1 <= age < 7:
                    risks.append("NEW_BORN") # No es un descarte, es una etiqueta

                return SignalResult(
                    token_symbol=symbol,
                    score=int(total_score), # Sin decimales para el log
                    net_flow_usd=int(net_flow_24h),
                    risk_factors=risks,
                    is_valid=len([r for r in risks if r == "FOMO_ZONE"]) == 0
                )
            except Exception as e:
                logger.error(f"Error técnico {symbol}: {e}")
                return None