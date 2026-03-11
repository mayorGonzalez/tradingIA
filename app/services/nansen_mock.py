"""
NansenMockClient — Cliente Mock Mejorado para Testing en DEBUG_MODE
====================================================================
Simula datos realistas de Nansen API con diferentes escenarios:
  • Bullish: Tokens en tendencia alcista (para operaciones ganadoras)
  • Bearish: Tokens en tendencia bajista (para evitar)
  • Accumulation: Smart Money acumulando (presionado de entrada)
  • Distribution: Smart Money distribuyendo (presión de salida)

Uso:
    DEBUG_MODE = True → Usa NansenMockClient automáticamente
    Genera datos reproducibles para testing repetible
"""

import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from loguru import logger

from app.models.nansen import SmartMoneyFlow, SmartMoneyHolding, DexTrade


class NansenMockClient:
    """
    Cliente mock que simula la API de Nansen con datos realistas.
    
    Características:
    - Genera flujos coherentes (no random puro)
    - Tokens con patrones reconocibles para debugging
    - Volúmenes realistas
    - Timestamps sincronizados
    """

    def __init__(self, seed: int = 42):
        """
        Args:
            seed: Semilla para reproducibilidad (mismo seed = mismos datos)
        """
        random.seed(seed)
        self.seed = seed
        self.session_id = datetime.now(timezone.utc).timestamp()
        logger.info(f"🛠️ NansenMockClient inicializado (seed={seed})")

    async def get_smart_money_flows(self) -> List[SmartMoneyFlow]:
        """
        Retorna flujos de Smart Money simulados.
        
        Patrón:
        - BTC: Patrón BULLISH consistente (+$5M/día)
        - ETH: Patrón ACCUMULATION (+$3M/día)
        - SOL: Patrón DISTRIBUTION (-$2M/día)
        - XRP: Patrón BEARISH (-$4M/día)
        - DOGE: Patrón PUMP (volatile)
        """

        # Unique addresses for mock tokens
        addr_btc = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
        addr_eth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        addr_sol = "0xSo11111111111111111111111111111111111111111"
        addr_xrp = "0x1d2f0da1690b98c50772161d51a1a368b715974c"
        addr_doge = "0x4206942069420694206942069420694206942069"
        addr_avax = "0x85f136f7e90264102ff940c6a38618fce1b88e1e"
        addr_link = "0x514910771af9ca656af840dff83e8264ecf986ca"
        addr_matic = "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0"

        flows = [
            # 1. Bitcoin - Tendencia Alcista Sostenida (BUY SIGNAL)
            SmartMoneyFlow(
                token_symbol="BTC",
                total_value_usd=450_000_000.0,
                value_usd=450_000_000.0,
                token_address=addr_btc,
                chain="bitcoin",
                wallet_count=47,
                percentage_of_holdings=35.2,
                entry_timestamp=int((datetime.now(timezone.utc) - timedelta(days=120)).timestamp()),
                avg_entry_price=62_500.0,
                current_pnl_percent=9.2,
                metadata={
                    "pattern": "bullish_accumulation",
                    "confidence": 0.92,
                    "risk_factors": [],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 2. Ethereum - Acumulación Gradual (ENTRY SIGNAL)
            SmartMoneyFlow(
                token_symbol="ETH",
                total_value_usd=280_000_000.0,
                value_usd=280_000_000.0,
                token_address=addr_eth,
                chain="ethereum",
                wallet_count=35,
                percentage_of_holdings=21.8,
                entry_timestamp=int((datetime.now(timezone.utc) - timedelta(days=95)).timestamp()),
                avg_entry_price=2_100.0,
                current_pnl_percent=12.5,
                metadata={
                    "pattern": "accumulation_phase",
                    "confidence": 0.85,
                    "risk_factors": ["low_volume"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 3. Solana - Distribución de Smart Money (AVOID SIGNAL)
            SmartMoneyFlow(
                token_symbol="SOL",
                total_value_usd=180_000_000.0,
                value_usd=180_000_000.0,
                token_address=addr_sol,
                chain="solana",
                wallet_count=22,
                percentage_of_holdings=18.5,
                entry_timestamp=int((datetime.now(timezone.utc) - timedelta(days=78)).timestamp()),
                avg_entry_price=145.0,
                current_pnl_percent=-4.2,
                metadata={
                    "pattern": "distribution_phase",
                    "confidence": 0.78,
                    "risk_factors": ["sell_pressure", "large_outflows"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 4. XRP - Tendencia Bajista (REJECT SIGNAL)
            SmartMoneyFlow(
                token_symbol="XRP",
                total_value_usd=95_000_000.0,
                value_usd=95_000_000.0,
                token_address=addr_xrp,
                chain="ripple",
                metadata={
                    "pattern": "distribution_phase",
                    "confidence": 0.78,
                    "risk_factors": ["sell_pressure", "large_outflows"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 4. XRP - Tendencia Bajista (REJECT SIGNAL)
            SmartMoneyFlow(
                token_symbol="XRP",
                net_flow_usd=-4_300_000.0,
                net_flow_7d_usd=-22_100_000.0,
                trader_count=8,
                exchange_netflow=2_800_000.0,
                whales_accumulating=0,
                chain="ripple",
                token_address=addr_xrp,
                metadata={
                    "pattern": "bearish_downtrend",
                    "confidence": 0.88,
                    "risk_factors": ["negative_flow", "whale_selling", "high_outflow"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 5. Dogecoin - Patrón Volátil (RISKY)
            SmartMoneyFlow(
                token_symbol="DOGE",
                net_flow_usd=1_800_000.0,      # Inflow pero volatile
                net_flow_7d_usd=-3_200_000.0,  # Negativo en 7 días (reversal)
                trader_count=18,
                exchange_netflow=600_000.0,
                whales_accumulating=2,
                chain="dogecoin",
                token_address=addr_doge,
                    metadata={
                    "pattern": "volatile_fomo",
                    "confidence": 0.45,  # Baja confianza
                    "risk_factors": ["extreme_volatility", "retail_driven", "low_whale_interest"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 6. Avalanche - Patrón Neutral (WAIT SIGNAL)
            SmartMoneyFlow(
                token_symbol="AVAX",
                net_flow_usd=450_000.0,
                net_flow_7d_usd=1_200_000.0,
                trader_count=12,
                exchange_netflow=-200_000.0,
                whales_accumulating=1,
                chain="avalanche",
                token_address=addr_avax,
                metadata={
                    "pattern": "consolidation",
                    "confidence": 0.65,
                    "risk_factors": ["low_volume", "indecisive"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 7. Chainlink - Acumulación Silenciosa (HIDDEN GEM)
            SmartMoneyFlow(
                token_symbol="LINK",
                net_flow_usd=2_750_000.0,
                net_flow_7d_usd=14_500_000.0,
                trader_count=29,
                exchange_netflow=-1_100_000.0,
                whales_accumulating=7,
                chain="chainlink",
                token_address=addr_link,
                metadata={
                    "pattern": "quiet_accumulation",
                    "confidence": 0.82,
                    "risk_factors": [],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),

            # 8. Polygon - Pequeño pump (CAUTION)
            SmartMoneyFlow(
                token_symbol="MATIC",
                net_flow_usd=950_000.0,
                net_flow_7d_usd=2_100_000.0,
                trader_count=15,
                exchange_netflow=-500_000.0,
                whales_accumulating=2,
                chain="polygon",
                token_address=addr_matic,
                metadata={
                    "pattern": "micro_accumulation",
                    "confidence": 0.68,
                    "risk_factors": ["low_liquidity"],
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            ),
        ]

        await asyncio.sleep(0.1)  # Simular latencia de red
        logger.info(f"📊 Mock: {len(flows)} flujos generados")
        return flows

    async def get_smart_money_holdings(self) -> List[SmartMoneyHolding]:
        """
        Retorna tokens que Smart Money ya tiene en cartera.
        
        Estos indican posiciones CONFIRMADAS de largo plazo (muy bullish).
        """
        # Use the same addresses as in flows for consistency
        addr_btc = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
        addr_eth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        addr_link = "0x514910771af9ca656af840dff83e8264ecf986ca"
        addr_avax = "0x85f136f7e90264102ff940c6a38618fce1b88e1e"

        holdings = [
            SmartMoneyHolding(
                token_symbol="BTC",
                token_address=addr_btc,
                chain="bitcoin",
                value_usd=450_000_000.0,
                holders_count=47,
                balance_24h_percent_change=0.5,
                share_of_holdings_percent=35.2,
                metadata={
                    "confidence": "very_high",
                    "conviction": "long_term_hold",
                    "tier": "mega_whale"
                }
            ),

            SmartMoneyHolding(
                token_symbol="ETH",
                token_address=addr_eth,
                chain="ethereum",
                value_usd=280_000_000.0,
                holders_count=35,
                balance_24h_percent_change=1.2,
                share_of_holdings_percent=21.8,
                metadata={
                    "confidence": "high",
                    "conviction": "long_term_hold",
                    "tier": "whale"
                }
            ),

            SmartMoneyHolding(
                token_symbol="LINK",
                token_address=addr_link,
                chain="chainlink",
                value_usd=85_000_000.0,
                holders_count=29,
                balance_24h_percent_change=-0.3,
                share_of_holdings_percent=6.6,
                metadata={
                    "confidence": "high",
                    "conviction": "accumulation_phase",
                    "tier": "whale"
                }
            ),

            SmartMoneyHolding(
                token_symbol="AVAX",
                token_address=addr_avax,
                chain="avalanche",
                value_usd=45_000_000.0,
                holders_count=12,
                balance_24h_percent_change=5.7,
                share_of_holdings_percent=3.5,
                metadata={
                    "confidence": "medium",
                    "conviction": "test_position",
                    "tier": "big_fish"
                }
            ),
        ]

        await asyncio.sleep(0.1)
        logger.info(f"💼 Mock: {len(holdings)} holdings generados")
        return holdings

    async def get_dex_trades(self) -> List[DexTrade]:
        """
        Retorna trades recientes en DEX (intercambios descentralizados).
        
        Indica ACTIVIDAD ACTUAL de Smart Money (últimas 24h).
        """
        # Consistent addresses
        addr_btc = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
        addr_usdc = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
        addr_eth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        addr_link = "0x514910771af9ca656af840dff83e8264ecf986ca"
        addr_avax = "0x85f136f7e90264102ff940c6a38618fce1b88e1e"
        addr_sol = "0xSo11111111111111111111111111111111111111111"
        addr_xrp = "0x1d2f0da1690b98c50772161d51a1a368b715974c"
        addr_usdt = "0xdac17f958d2ee523a2206206994597c13d831ec7"

        trades = [
            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
                transaction_hash=f"0x{'a'*64}",
                trader_address="0x" + "b" * 40,
                token_sold_symbol="USDC",
                token_sold_address=addr_usdc,
                token_bought_symbol="BTC",
                token_bought_address=addr_btc,
                trade_value_usd=500_000.0
            ),

            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
                transaction_hash=f"0x{'c'*64}",
                trader_address="0x" + "d" * 40,
                token_sold_symbol="USDT",
                token_sold_address=addr_usdt,
                token_bought_symbol="ETH",
                token_bought_address=addr_eth,
                trade_value_usd=300_000.0
            ),

            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=5),
                transaction_hash=f"0x{'e'*64}",
                trader_address="0x" + "f" * 40,
                token_sold_symbol="USDC",
                token_sold_address=addr_usdc,
                token_bought_symbol="LINK",
                token_bought_address=addr_link,
                trade_value_usd=200_000.0
            ),

            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                transaction_hash=f"0x{'1'*64}",
                trader_address="0x" + "2" * 40,
                token_sold_symbol="USDT",
                token_sold_address=addr_usdt,
                token_bought_symbol="AVAX",
                token_bought_address=addr_avax,
                trade_value_usd=150_000.0
            ),

            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=4),
                transaction_hash=f"0x{'3'*64}",
                trader_address="0x" + "4" * 40,
                token_sold_symbol="SOL",
                token_sold_address=addr_sol,
                token_bought_symbol="USDC",
                token_bought_address=addr_usdc,
                trade_value_usd=180_000.0
            ),

            DexTrade(
                chain="ethereum",
                block_timestamp=datetime.now(timezone.utc) - timedelta(hours=6),
                transaction_hash=f"0x{'5'*64}",
                trader_address="0x" + "6" * 40,
                token_sold_symbol="XRP",
                token_sold_address=addr_xrp,
                token_bought_symbol="USDT",
                token_bought_address=addr_usdt,
                trade_value_usd=15_000.0
            ),
        ]

        await asyncio.sleep(0.1)
        logger.info(f"🔄 Mock: {len(trades)} DEX trades generados")
        return trades

    def get_debug_summary(self) -> dict:
        """
        Retorna resumen para debugging en consola.
        """
        return {
            "mode": "DEBUG_MOCK",
            "seed": self.seed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": "Mock data generator para testing del bot en dev",
            "test_scenarios": {
                "BTC": "✅ Bullish - Strong buy signal",
                "ETH": "✅ Accumulation - Good entry",
                "SOL": "⚠️ Distribution - Exit signal",
                "XRP": "❌ Bearish - Avoid",
                "DOGE": "⚠️ Volatile - Risky",
                "AVAX": "⏸️ Consolidation - Wait",
                "LINK": "✅ Hidden gem - Quiet accumulation",
                "MATIC": "⚠️ Caution - Low liquidity",
            },
            "total_flows": 8,
            "total_holdings": 4,
            "total_dex_trades": 6,
        }