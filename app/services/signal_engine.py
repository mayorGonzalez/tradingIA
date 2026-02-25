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
        exchange_client: ExchangeClient,
        portfolio_service: PortfolioService,
        min_inflow_usd: float = 1000.0
    ):
        self.exchange = exchange_client
        self.portfolio = portfolio_service
        self.min_inflow_usd = min_inflow_usd

    async def analyze_flows(
        self,
        flows: List[SmartMoneyFlow],
        holdings: List[SmartMoneyHolding] | None = None,
        dex_trades: List[DexTrade] | None = None,
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
            if trade.token_sold_symbol in ("ETH", "USDT", "USDC", "WETH", "DAI"):
                dex_buy_counts[trade.token_bought_symbol] += 1

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
        validated = await asyncio.gather(*tasks, return_exceptions=False)

        results = [r for r in validated if r is not None]
        
        # Ordenar por score descendente
        results.sort(key=lambda r: r.score, reverse=True)
        
        valid_count = sum(1 for r in results if r.is_valid)
        logger.info(
            f"Scoring completado → {len(results)} candidatos, "
            f"{valid_count} superan umbral de {settings.MIN_SCORE_THRESHOLD}pts"
        )
        return results

    async def _validate_signal(
        self,
        row: pd.Series,
        held_symbols: Set[str],
        dex_buy_counts: Counter,
    ) -> SignalResult | None:
        """Calcula el score 0-100 y valida técnicamente un token candidato."""
        symbol = row['token_symbol']
        net_flow_24h = float(row['net_flow_usd'])
        net_flow_7d = float(row.get('net_flow_7d_usd', 0.0))
        trader_count = int(row.get('trader_count', 0))
        risk_factors: List[str] = []

        # =====================================================================
        # DIMENSIÓN 1 — VOLUMEN NETO (peso: SCORE_WEIGHT_FLOW = 40%)
        # Puntuación proporcional al inflow detectado.
        # Se normaliza contra 10x el umbral mínimo para llegar a 100pts.
        # =====================================================================
        vol_score = min((net_flow_24h / (self.min_inflow_usd * 10)) * 100, 100)

        # Bonus por confirmación en 7 días (tesis no es un flush puntual)
        trend_confirmed_7d = net_flow_7d > 0 and net_flow_7d >= net_flow_24h
        if trend_confirmed_7d:
            vol_score = min(vol_score * 1.15, 100)  # +15% bonus

        # =====================================================================
        # DIMENSIÓN 2 — CONCENTRACIÓN / CALIDAD DE WALLETS (peso: 30%)
        # Fuente 1: si el token ya está en Holdings → señal muy fuerte
        # Fuente 2: trader_count del endpoint netflow
        # =====================================================================
        conc_score = 0.0

        # ¿Lo tiene Smart Money en cartera (Holdings)?
        in_holdings = symbol in held_symbols
        if in_holdings:
            conc_score += 70  # Posición sostenida = altísima calidad

        # Cuántas wallets distintas están comprando (más = mejor diversificación)
        if trader_count >= 10:
            conc_score = min(conc_score + 30, 100)
        elif trader_count >= 5:
            conc_score = min(conc_score + 20, 100)
        elif trader_count >= 2:
            conc_score = min(conc_score + 10, 100)

        # =====================================================================
        # DIMENSIÓN 3 — PERSISTENCIA / ACTIVIDAD EN DEX (peso: 30%)
        # Fuente 1: DEX trades recientes de Smart Money en este token
        # Fuente 2: historial de trades previos en nuestra DB
        # =====================================================================
        dex_buys = dex_buy_counts.get(symbol, 0)
        dex_score = min((dex_buys / 5) * 100, 100)   # 5+ compras DEX = 100pts

        is_persistent_db = await self.portfolio.check_persistence(symbol)
        if is_persistent_db:
            dex_score = min(dex_score + 30, 100)

        # =====================================================================
        # SCORE TOTAL PONDERADO
        # =====================================================================
        total_score = (
            vol_score  * settings.SCORE_WEIGHT_FLOW +
            conc_score * settings.SCORE_WEIGHT_CONCENTRATION +
            dex_score  * settings.SCORE_WEIGHT_PERSISTENCE
        )

        # Descarte temprano: no consultar Exchange si el score preliminar es muy bajo
        if total_score < 50:
            return None

        # =====================================================================
        # VALIDACIÓN TÉCNICA VÍA EXCHANGE
        # =====================================================================
        price_change_1h: float | None = None
        exchange_vol_24h: float | None = None

        try:
            price_change_1h, exchange_vol_24h = await asyncio.gather(
                self.exchange.get_price_change_1h(symbol),
                self.exchange.get_24h_volume(symbol),
                return_exceptions=False
            )
        except Exception as e:
            logger.warning(f"[SignalEngine] No se pudo obtener datos técnicos para {symbol}: {e}")
            risk_factors.append("TECHNICAL_DATA_UNAVAILABLE")

        # Filtro Anti-Pump: No entrar si ya ha subido > MAX_PRICE_CHANGE_1H_PCT en 1h
        if price_change_1h is not None and price_change_1h > settings.MAX_PRICE_CHANGE_1H_PCT:
            risk_factors.append("PUMP_EXHAUSTION")

        # Filtro de Liquidez: El inflow no debe superar el 50% del volumen de Exchange
        if exchange_vol_24h and exchange_vol_24h > 0 and (net_flow_24h > exchange_vol_24h * 0.5):
            risk_factors.append("LOW_EXCHANGE_LIQUIDITY")

        # Filtro Token Joven: tokens < 7 días son muy volátiles
        token_age = int(row.get('token_age_days') or 0)
        if 0 < token_age < 7:
            risk_factors.append("VERY_NEW_TOKEN")

        # Decisión final
        is_valid = (
            total_score >= settings.MIN_SCORE_THRESHOLD
            and "PUMP_EXHAUSTION" not in risk_factors
        )

        logger.debug(
            f"[{symbol}] Score={total_score:.1f} "
            f"(vol={vol_score:.0f} conc={conc_score:.0f} dex={dex_score:.0f}) "
            f"held={in_holdings} dex_buys={dex_buys} "
            f"risks={risk_factors} valid={is_valid}"
        )

        return SignalResult(
            token_symbol=symbol,
            score=round(total_score, 2),
            net_flow_usd=net_flow_24h,
            holders_count=trader_count,
            dex_buy_count=dex_buys,
            trend_confirmed_7d=trend_confirmed_7d,
            price_change_1h=price_change_1h,
            risk_factors=risk_factors,
            is_valid=is_valid,
        )