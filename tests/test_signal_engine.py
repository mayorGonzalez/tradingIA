import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.signal_engine import SignalEngine
from app.models.nansen import SmartMoneyFlow, SignalResult
from app.core.config import settings

@pytest.fixture
def mock_exchange():
    exchange = MagicMock()
    exchange.get_price_change_1h = AsyncMock(return_value=5.0)
    exchange.get_24h_volume = AsyncMock(return_value=1000000.0)
    return exchange

@pytest.fixture
def mock_portfolio():
    portfolio = MagicMock()
    portfolio.check_persistence = AsyncMock(return_value=False)
    return portfolio

@pytest.mark.asyncio
async def test_signal_score_above_threshold(mock_exchange, mock_portfolio):
    """Prueba que un token con altos inflow y holdings supere el umbral de 75."""
    engine = SignalEngine(mock_exchange, mock_portfolio, min_inflow_usd=1000.0)
    
    # Token con 25k de inflow (25x el mínimo -> vol_score alto)
    flow = SmartMoneyFlow(
        chain="ethereum",
        token_address="0x123",
        token_symbol="GOLD",
        net_flow_usd=25000.0,
        trader_count=15,
        token_sectors=["DeFi"]
    )
    
    # Simular que está en holdings (conc_score alto)
    results = await engine.analyze_flows([flow], holdings=[MagicMock(token_symbol="GOLD")])
    
    assert len(results) == 1
    assert results[0].token_symbol == "GOLD"
    assert results[0].score >= 75
    assert results[0].is_valid is True

@pytest.mark.asyncio
async def test_signal_pump_exhaustion(mock_exchange, mock_portfolio):
    """Prueba que un token con price change alto sea marcado como PUMP_EXHAUSTION."""
    # Simular un pump del 20% (> 15% límite)
    mock_exchange.get_price_change_1h.return_value = 20.0
    
    engine = SignalEngine(mock_exchange, mock_portfolio, min_inflow_usd=1000.0)
    
    flow = SmartMoneyFlow(
        chain="ethereum",
        token_address="0x456",
        token_symbol="MOON",
        net_flow_usd=15000.0,
        trader_count=12,
        token_sectors=["Meme"]
    )
    
    results = await engine.analyze_flows([flow])
    
    assert len(results) == 1
    assert "PUMP_EXHAUSTION" in results[0].risk_factors
    assert results[0].is_valid is False
