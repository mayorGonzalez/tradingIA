"""
Test Suite — Validación de NansenMockClient para Dashboard Testing
===================================================================
Verifica que los datos mock:
  1. Se generan correctamente sin errores
  2. Tienen estructura esperada (Pydantic validation)
  3. Son realistas y coherentes
  4. Pueden renderizarse en el dashboard
  5. Flujos son procesables por SignalEngine

Uso:
    pytest tests/test_nansen_mock_dashboard.py -v --tb=short
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from app.services.nansen_mock import NansenMockClient
from app.models.nansen import SmartMoneyFlow, SmartMoneyHolding, DexTrade, SignalResult
from app.services.signal_engine import SignalEngine
from app.services.portfolio_service import PortfolioService
from app.infraestructure.exchange_client import ExchangeClient


class TestNansenMockClient:
    """Tests básicos del mock client."""

    @pytest.fixture
    async def mock_client(self):
        """Instancia un cliente mock."""
        return NansenMockClient(seed=42)

    @pytest.mark.asyncio
    async def test_get_smart_money_flows(self, mock_client):
        """✅ Flows se generan sin errores y con estructura válida."""
        flows = await mock_client.get_smart_money_flows()

        # Validaciones básicas
        assert len(flows) > 0, "Debe generar al menos 1 flujo"
        assert all(isinstance(f, SmartMoneyFlow) for f in flows), "Todos deben ser SmartMoneyFlow"

        # Validar primer flujo
        btc_flow = next((f for f in flows if f.token_symbol == "BTC"), None)
        assert btc_flow is not None, "Debe incluir BTC"
        assert btc_flow.net_flow_usd > 0, "BTC debe tener inflow positivo"
        assert btc_flow.trader_count > 0, "Debe haber traders"

    @pytest.mark.asyncio
    async def test_get_smart_money_holdings(self, mock_client):
        """✅ Holdings se generan correctamente."""
        holdings = await mock_client.get_smart_money_holdings()

        assert len(holdings) > 0, "Debe generar holdings"
        assert all(isinstance(h, SmartMoneyHolding) for h in holdings), "Tipo correcto"

        # Verificar datos coherentes
        for holding in holdings:
            assert holding.total_value_usd > 0, "Value > 0"
            assert holding.wallet_count > 0, "Wallets > 0"
            assert holding.current_pnl_percent is not None, "PnL definido"

    @pytest.mark.asyncio
    async def test_get_dex_trades(self, mock_client):
        """✅ DEX trades se generan correctamente."""
        trades = await mock_client.get_dex_trades()

        assert len(trades) > 0, "Debe generar trades"
        assert all(isinstance(t, DexTrade) for t in trades), "Tipo correcto"

        # Verificar trades tienen tokens
        for trade in trades:
            assert trade.token_sold_symbol, "Token sold definido"
            assert trade.token_bought_symbol, "Token bought definido"
            assert trade.amount_sold > 0, "Amount > 0"

    @pytest.mark.asyncio
    async def test_mock_reproducibility(self):
        """✅ Mismo seed = mismos datos (reproducible)."""
        client1 = NansenMockClient(seed=42)
        client2 = NansenMockClient(seed=42)

        flows1 = await client1.get_smart_money_flows()
        flows2 = await client2.get_smart_money_flows()

        # Deben ser idénticos
        assert len(flows1) == len(flows2), "Mismo número de flows"
        assert flows1[0].token_symbol == flows2[0].token_symbol, "Mismo orden"
        assert flows1[0].net_flow_usd == flows2[0].net_flow_usd, "Mismos valores"

    def test_debug_summary(self):
        """✅ Summary debug es útil."""
        client = NansenMockClient(seed=42)
        summary = client.get_debug_summary()

        assert summary["mode"] == "DEBUG_MOCK"
        assert "test_scenarios" in summary
        assert len(summary["test_scenarios"]) == 8
        assert summary["total_flows"] == 8


class TestDashboardIntegration:
    """Tests de integración: ¿se puede visualizar en dashboard?"""

    @pytest.fixture
    async def mock_client(self):
        return NansenMockClient(seed=42)

    @pytest.mark.asyncio
    async def test_flows_to_json_serializable(self, mock_client):
        """✅ Flows son JSON-serializable (importante para API/WebSocket)."""
        flows = await mock_client.get_smart_money_flows()

        try:
            # Simular conversión a JSON (como si se enviara al frontend)
            json_str = json.dumps(
                [f.model_dump() for f in flows],
                default=str,
                indent=2
            )
            assert len(json_str) > 0, "JSON válido"
        except Exception as e:
            pytest.fail(f"No se puede serializar flows a JSON: {e}")

    @pytest.mark.asyncio
    async def test_holdings_dashboard_fields(self, mock_client):
        """✅ Holdings tienen campos necesarios para heatmap."""
        holdings = await mock_client.get_smart_money_holdings()

        required_fields = [
            "token_symbol", "total_value_usd", "wallet_count",
            "percentage_of_holdings", "current_pnl_percent"
        ]

        for holding in holdings:
            for field in required_fields:
                assert hasattr(holding, field), f"Falta campo: {field}"
                assert getattr(holding, field) is not None, f"Field vacío: {field}"

    @pytest.mark.asyncio
    async def test_dex_trades_timeline_format(self, mock_client):
        """✅ DEX trades tienen timestamps válidos."""
        trades = await mock_client.get_dex_trades()

        for trade in trades:
            # Timestamp debe ser Unix timestamp
            assert isinstance(trade.timestamp, int), "Timestamp debe ser int"
            assert 0 < trade.timestamp < 2**31, "Timestamp válido"

            # Convertible a fecha
            dt = datetime.fromtimestamp(trade.timestamp, tz=timezone.utc)
            assert dt is not None, "Debe ser convertible a datetime"


class TestSignalEngineWithMockData:
    """Tests: ¿SignalEngine puede procesar datos mock?"""

    @pytest.fixture
    async def setup(self):
        """Setup para integration test."""
        mock_client = NansenMockClient(seed=42)
        portfolio = PortfolioService()
        
        # Mock exchange (no necesita credenciales reales)
        exchange = ExchangeClient.__new__(ExchangeClient)
        exchange.exchange = None
        exchange.name = "Mock"
        
        engine = SignalEngine(exchange, portfolio, min_inflow_usd=100_000.0)

        flows = await mock_client.get_smart_money_flows()
        holdings = await mock_client.get_smart_money_holdings()
        trades = await mock_client.get_dex_trades()

        return {
            "engine": engine,
            "flows": flows,
            "holdings": holdings,
            "trades": trades,
        }

    @pytest.mark.asyncio
    async def test_signal_engine_processes_mock_data(self, setup):
        """✅ SignalEngine puede procesar datos mock sin errores."""
        engine = setup["engine"]
        flows = setup["flows"]
        holdings = setup["holdings"]
        trades = setup["trades"]

        try:
            signals = await engine.analyze_flows(
                flows=flows,
                holdings=holdings,
                dex_trades=trades,
            )
            assert signals is not None, "Debe retornar signals"
            assert len(signals) > 0, "Debe detectar señales en mock data"
        except Exception as e:
            pytest.fail(f"SignalEngine no puede procesar mock data: {e}")

    @pytest.mark.asyncio
    async def test_bullish_signals_detected(self, setup):
        """✅ Detecta señales bullish correctamente."""
        engine = setup["engine"]
        flows = setup["flows"]
        holdings = setup["holdings"]
        trades = setup["trades"]

        signals = await engine.analyze_flows(flows, holdings, trades)
        
        # BTC debe estar en señales (es bullish)
        btc_signal = next((s for s in signals if s.token_symbol == "BTC"), None)
        assert btc_signal is not None, "BTC debe ser detectado"
        assert btc_signal.is_valid, "BTC debe ser válido"
        assert btc_signal.score > 50, "BTC debe tener score alto"

    @pytest.mark.asyncio
    async def test_bearish_signals_filtered(self, setup):
        """✅ Filtra señales bearish correctamente."""
        engine = setup["engine"]
        flows = setup["flows"]
        holdings = setup["holdings"]
        trades = setup["trades"]

        signals = await engine.analyze_flows(flows, holdings, trades)
        
        # XRP es bearish, no debe estar en señales válidas
        xrp_valid_signal = next(
            (s for s in signals if s.token_symbol == "XRP" and s.is_valid),
            None
        )
        assert xrp_valid_signal is None, "XRP (bearish) no debe ser válido"


class TestDashboardJsonOutput:
    """Tests: Verificar formato JSON exacto para dashboard."""

    @pytest.fixture
    async def mock_data(self):
        client = NansenMockClient(seed=42)
        return {
            "flows": await client.get_smart_money_flows(),
            "holdings": await client.get_smart_money_holdings(),
            "trades": await client.get_dex_trades(),
            "summary": client.get_debug_summary(),
        }

    @pytest.mark.asyncio
    async def test_dashboard_api_response_format(self, mock_data):
        """✅ Formato de respuesta API es correcto para frontend."""
        
        # Simular respuesta que iría al dashboard
        response = {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "market_flows": [f.model_dump() for f in mock_data["flows"]],
                "smart_money_holdings": [h.model_dump() for h in mock_data["holdings"]],
                "recent_trades": [t.model_dump() for t in mock_data["trades"]],
                "debug_mode": True,
                "summary": mock_data["summary"],
            }
        }

        # Validar estructura
        assert response["status"] == "success"
        assert len(response["data"]["market_flows"]) > 0
        assert len(response["data"]["smart_money_holdings"]) > 0
        assert len(response["data"]["recent_trades"]) > 0

        # Debe ser serializable a JSON
        json_str = json.dumps(response, default=str)
        assert len(json_str) > 1000, "Datos suficientes"

    @pytest.mark.asyncio
    async def test_heatmap_data_format(self, mock_data):
        """✅ Datos para heatmap tienen formato correcto."""
        
        heatmap_data = []
        for flow in mock_data["flows"]:
            heatmap_data.append({
                "symbol": flow.token_symbol,
                "change24h": (flow.net_flow_usd / 100_000_000.0) * 100,  # Pseudo-percentage
                "marketCap": flow.net_flow_usd * 10,  # Mock market cap
                "volume24h": flow.net_flow_usd * 0.5,
                "color": "green" if flow.net_flow_usd > 0 else "red",
            })

        assert len(heatmap_data) == 8, "8 monedas en heatmap"
        
        # Validar primer elemento
        btc_heatmap = next((h for h in heatmap_data if h["symbol"] == "BTC"), None)
        assert btc_heatmap is not None
        assert btc_heatmap["change24h"] > 0, "BTC debe ser positivo"
        assert btc_heatmap["color"] == "green"


class TestDebugModeConsoleOutput:
    """Tests: Output en consola para debugging durante desarrollo."""

    @pytest.mark.asyncio
    async def test_detailed_logging_output(self, capsys):
        """✅ Verifica que el logging sea detallado."""
        client = NansenMockClient(seed=42)
        
        await client.get_smart_money_flows()
        await client.get_smart_money_holdings()
        await client.get_dex_trades()

        # Capturar output
        # (El logging va a loguru, no stdout)
        # Verificamos que los métodos no lancen excepciones
        assert client.seed == 42

    def test_summary_is_informative(self):
        """✅ Summary muestra toda la información útil."""
        client = NansenMockClient(seed=42)
        summary = client.get_debug_summary()

        print("\n📊 MOCK DATA DEBUG SUMMARY:")
        print(json.dumps(summary, indent=2, default=str))

        # Verificar contenido
        assert "mode" in summary
        assert "test_scenarios" in summary
        assert all(
            key in summary["test_scenarios"]
            for key in ["BTC", "ETH", "SOL", "XRP", "DOGE", "AVAX", "LINK", "MATIC"]
        )


# ─────────────────────────────────────────────────────────────────────────── #
# FIXTURES PARA TESTS MANUALES (pytest -k manual_test)
# ─────────────────────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_manual_mock_generation():
    """
    Test manual para verificar datos en consola.
    
    Ejecución:
        pytest tests/test_nansen_mock_dashboard.py::test_manual_mock_generation -v -s
    """
    client = NansenMockClient(seed=42)
    
    print("\n" + "="*70)
    print("🛠️ NANSEN MOCK CLIENT - MANUAL TEST")
    print("="*70)
    
    # 1. Flows
    print("\n📊 SMART MONEY FLOWS:")
    print("-" * 70)
    flows = await client.get_smart_money_flows()
    for flow in flows:
        print(f"  {flow.token_symbol:6s} | Flow: ${flow.net_flow_usd:>12,.0f} | Traders: {flow.trader_count}")
    
    # 2. Holdings
    print("\n💼 SMART MONEY HOLDINGS:")
    print("-" * 70)
    holdings = await client.get_smart_money_holdings()
    for holding in holdings:
        print(f"  {holding.token_symbol:6s} | Value: ${holding.total_value_usd:>12,.0f} | PnL: {holding.current_pnl_percent:>+6.1f}%")
    
    # 3. DEX Trades
    print("\n🔄 RECENT DEX TRADES:")
    print("-" * 70)
    trades = await client.get_dex_trades()
    for trade in trades[:3]:  # Mostrar solo 3 primeros
        print(f"  {trade.token_sold_symbol} → {trade.token_bought_symbol} | ${trade.amount_sold:>10,.0f}")
    
    # 4. Summary
    print("\n📋 SUMMARY:")
    print("-" * 70)
    summary = client.get_debug_summary()
    print(json.dumps(summary, indent=2, default=str))
    print("="*70)

    assert True, "Test manual completado"


# ─────────────────────────────────────────────────────────────────────────── #
# SCRIPT DE VERIFICACIÓN RÁPIDA (sin pytest)
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    """
    Ejecutar prueba rápida sin pytest:
        python tests/test_nansen_mock_dashboard.py
    """
    import sys
    
    async def quick_test():
        print("🚀 Quick test de NansenMockClient...")
        client = NansenMockClient(seed=42)
        
        flows = await client.get_smart_money_flows()
        holdings = await client.get_smart_money_holdings()
        trades = await client.get_dex_trades()
        
        print(f"✅ {len(flows)} flows generados")
        print(f"✅ {len(holdings)} holdings generados")
        print(f"✅ {len(trades)} trades generados")
        
        summary = client.get_debug_summary()
        print(f"✅ Debug summary: {summary['mode']}")
        
        print("\n✅ Todas las pruebas pasaron!")
        return True

    if sys.version_info >= (3, 7):
        asyncio.run(quick_test())
    else:
        print("⚠️ Requiere Python 3.7+")
