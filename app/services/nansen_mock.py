from datetime import datetime, timezone
from app.models.nansen import (
    NansenResponse, SmartMoneyFlow, SmartMoneyHolding, DexTrade
)
from typing import List


class NansenMockClient:
    """Simulador de Nansen para testeos sin coste."""

    async def get_smart_money_flows(self, chain: str = "ethereum", **kwargs) -> NansenResponse:
        mock_data = [
            SmartMoneyFlow(
                chain=chain,
                token_address="0x123...abc",
                token_symbol="GOLD_TOKEN",
                net_flow_usd=50000.0,
                net_flow_1h_usd=5000.0,
                net_flow_7d_usd=80000.0,
                net_flow_30d_usd=200000.0,
                trader_count=8,
                token_age_days=120,
                market_cap_usd=5_000_000.0,
                token_sectors=["DeFi"],
                labels=["Funds", "DEX Traders"]
            ),
            SmartMoneyFlow(
                chain=chain,
                token_address="0x456...def",
                token_symbol="DUMP_COIN",
                net_flow_usd=-10000.0,
                trader_count=1,
                token_age_days=3,
                labels=["Whale"]
            ),
        ]
        return NansenResponse(data=mock_data, total_records=2)

    async def get_smart_money_holdings(self, chain: str = "ethereum") -> List[SmartMoneyHolding]:
        return [
            SmartMoneyHolding(
                chain=chain,
                token_address="0x123...abc",
                token_symbol="GOLD_TOKEN",
                value_usd=1_200_000.0,
                holders_count=12,
                balance_24h_percent_change=2.5,
                share_of_holdings_percent=0.05,
                token_age_days=120,
                market_cap_usd=5_000_000.0,
                token_sectors=["DeFi"],
            )
        ]

    async def get_dex_trades(self, chain: str = "ethereum") -> List[DexTrade]:
        now = datetime.now(timezone.utc)
        return [
            DexTrade(
                chain=chain,
                block_timestamp=now,
                transaction_hash="0xabc123",
                trader_address="0xfund1",
                trader_address_label="Fund Alpha",
                token_bought_symbol="GOLD_TOKEN",
                token_sold_symbol="ETH",
                token_bought_address="0x123...abc",
                token_sold_address="0xEEEE",
                trade_value_usd=15_000.0,
                token_bought_age_days=120,
                token_bought_market_cap=5_000_000.0,
            ),
            DexTrade(
                chain=chain,
                block_timestamp=now,
                transaction_hash="0xdef456",
                trader_address="0xfund2",
                trader_address_label="Smart Trader",
                token_bought_symbol="GOLD_TOKEN",
                token_sold_symbol="USDC",
                token_bought_address="0x123...abc",
                token_sold_address="0xUSDC",
                trade_value_usd=8_000.0,
                token_bought_age_days=120,
                token_bought_market_cap=5_000_000.0,
            ),
        ]