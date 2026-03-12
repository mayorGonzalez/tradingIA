"""
Unit Tests — Risk Manager, Circuit Breaker, Exit Manager, Portfolio Service
=============================================================================
Cobertura objetivo: 80%+

Uso:
    pytest tests/test_core_services.py -v

Requisitos:
    pytest, pytest-asyncio
    pip install pytest pytest-asyncio
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ─── Módulos a testear ────────────────────────────────────────────────────── #
from app.services.risk_manager import RiskManager
from app.services.circuit_breaker import CircuitBreaker
from app.services.exit_manager import ExitManager
from app.services.portfolio_service import PortfolioService, Trade
from app.models.nansen import SignalResult


# ─── Fixtures helpers ─────────────────────────────────────────────────────── #

def make_signal(
    symbol: str = "ETH",
    score: float = 75.0,
    risk_factors: list | None = None,
    price_change_1h: float | None = 1.5,
) -> SignalResult:
    """Crea una señal mínima válida para pruebas."""
    return SignalResult(
        token_symbol=symbol,
        score=score,
        is_valid=True,
        risk_factors=risk_factors or [],
        price_change_1h=price_change_1h,
        net_flow_usd=200_000.0,
        holders_count=5,
        dex_buy_count=10,
    )


def make_trade(
    trade_id: int = 1,
    symbol: str = "ETH",
    entry_price: float = 3000.0,
    amount_usd: float = 100.0,
) -> Trade:
    """Crea un Trade DTO de prueba."""
    return Trade(
        id=trade_id,
        token_symbol=symbol,
        entry_price=entry_price,
        amount_usd=amount_usd,
        status="OPEN",
        entry_date=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  RISK MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════ #

class TestRiskManager:

    def test_validate_execution_ok(self):
        """Señal válida debe ser aprobada."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(score=80.0, risk_factors=[])
        result = rm.validate_execution(signal, available_balance=5000.0)
        assert result is True

    def test_validate_execution_rejects_low_balance(self):
        """Balance muy bajo → la inversión calculada cae por debajo del mínimo."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(score=80.0)
        # 10% de 50$ = 5$ < MIN_POSITION_SIZE_USD=10$
        result = rm.validate_execution(signal, available_balance=50.0)
        assert result is False

    def test_validate_execution_rejects_too_many_risk_factors(self):
        """Más de 2 factores de riesgo → rechazado."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(risk_factors=["vol_high", "liquidity_low", "downtrend"])
        result = rm.validate_execution(signal, available_balance=5000.0)
        assert result is False

    def test_validate_execution_rejects_freefall(self):
        """Token en caída libre (price_change_1h < STOP_LOSS_PCT) → rechazado."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(price_change_1h=-5.0)  # STOP_LOSS_PCT = -2.0
        result = rm.validate_execution(signal, available_balance=5000.0)
        assert result is False

    def test_validate_execution_rejects_fomo(self):
        """Token con alza explosiva (>50% en 1h) → filtro anti-FOMO."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(price_change_1h=60.0)  # MAX_PRICE_CHANGE_1H_PCT = 50
        result = rm.validate_execution(signal, available_balance=5000.0)
        assert result is False

    def test_validate_execution_rejects_reentry(self):
        """No debe permitir re-entrar al mismo token en el mismo ciclo."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        signal = make_signal(symbol="BTC")
        rm.register_trade("BTC", 100.0)
        result = rm.validate_execution(signal, available_balance=5000.0)
        assert result is False

    def test_calculate_position_size_bounded(self):
        """La posición calculada siempre debe estar entre MIN y MAX."""
        from app.core.config import settings
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        # Score muy bajo → debe acotarse al MIN
        size = rm.calculate_position_size(signal_score=5.0)
        assert size >= settings.MIN_POSITION_SIZE_USD

        # Balance enorme → no debe superar MAX
        size = rm.calculate_position_size(signal_score=100.0)
        assert size <= settings.MAX_POSITION_SIZE_USD

    def test_calculate_position_size_low_score_penalty(self):
        """Score < 50 debe reducir la posición adicional un 50%."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        size_low = rm.calculate_position_size(signal_score=40.0)
        size_high = rm.calculate_position_size(signal_score=80.0)
        assert size_low <= size_high

    def test_register_trade_increments_exposure(self):
        """register_trade debe aumentar la exposición actual."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        rm.register_trade("ETH", 200.0)
        assert rm.current_exposure == 200.0
        rm.register_trade("BTC", 100.0)
        assert rm.current_exposure == 300.0

    def test_reset_cycle_clears_symbols(self):
        """reset_cycle debe limpiar el historial del ciclo."""
        rm = RiskManager(total_equity_usd=10000.0, current_exposure_usd=0.0)
        rm.register_trade("ETH", 100.0)
        assert "ETH" in rm._traded_symbols_this_cycle
        rm.reset_cycle()
        assert rm._traded_symbols_this_cycle == []


# ═══════════════════════════════════════════════════════════════════════════ #
#  CIRCUIT BREAKER TESTS
# ═══════════════════════════════════════════════════════════════════════════ #

class TestCircuitBreaker:

    @pytest.mark.asyncio
    async def test_is_open_false_when_healthy(self):
        """Portfolio sano → circuito cerrado."""
        cb = CircuitBreaker(max_daily_drawdown_pct=5.0, max_open_trades=5)
        mock_portfolio = AsyncMock()
        mock_portfolio.get_open_trades.return_value = [make_trade()]  # 1 trade abierto
        mock_portfolio.get_daily_pnl.return_value = 50.0              # PnL positivo

        result = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_open_true_when_max_trades_reached(self):
        """Límite de trades alcanzado → circuito abierto."""
        cb = CircuitBreaker(max_open_trades=3)
        mock_portfolio = AsyncMock()
        mock_portfolio.get_open_trades.return_value = [make_trade(i) for i in range(3)]
        mock_portfolio.get_daily_pnl.return_value = 0.0

        result = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_open_true_when_drawdown_exceeded(self):
        """Drawdown excede el límite → circuito abierto."""
        cb = CircuitBreaker(max_daily_drawdown_pct=5.0, max_open_trades=10)
        mock_portfolio = AsyncMock()
        mock_portfolio.get_open_trades.return_value = []
        mock_portfolio.get_daily_pnl.return_value = -600.0  # Pérdida de $600 sobre $10k = 6%

        result = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result is True  # 5% de 10000 = -500$, -600 < -500

    @pytest.mark.asyncio
    async def test_is_open_true_on_exception(self):
        """Error al consultar portfolio → circuito abierto por seguridad."""
        cb = CircuitBreaker()
        mock_portfolio = AsyncMock()
        mock_portfolio.get_open_trades.side_effect = RuntimeError("DB error")

        result = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_break_duration_blocks_subsequent_calls(self):
        """El breaker debe bloquear llamadas durante la ventana de tiempo activa."""
        cb = CircuitBreaker(max_open_trades=1, break_duration_minutes=60)
        mock_portfolio = AsyncMock()
        mock_portfolio.get_open_trades.return_value = [make_trade(1), make_trade(2)]  # 2 > 1
        mock_portfolio.get_daily_pnl.return_value = 0.0

        # Primera llamada → activa el breaker
        result1 = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result1 is True

        # Segunda llamada (sin que haya pasado tiempo) → todavía bloqueado
        result2 = await cb.is_open(mock_portfolio, current_balance_usd=10_000.0)
        assert result2 is True

    def test_reset_clears_state(self):
        """reset() debe limpiar el estado del breaker."""
        cb = CircuitBreaker()
        cb._trip(reason="test")
        assert cb._is_still_tripped() is True
        cb.reset()
        assert cb._is_still_tripped() is False


# ═══════════════════════════════════════════════════════════════════════════ #
#  EXIT MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════ #

class TestExitManager:

    def _make_exit_manager(self):
        portfolio = AsyncMock()
        exchange = AsyncMock()
        notifier = AsyncMock()
        em = ExitManager(portfolio, exchange, notifier)
        return em, portfolio, exchange, notifier

    @pytest.mark.asyncio
    async def test_check_open_positions_no_trades(self):
        """Sin trades abiertos no debe hacer nada."""
        em, portfolio, exchange, notifier = self._make_exit_manager()
        portfolio.get_open_trades.return_value = []

        await em.check_open_positions()

        exchange.fetch_ticker.assert_not_called()

    @pytest.mark.asyncio
    async def test_take_profit_triggers_full_sell(self):
        """Cuando el PnL alcanza el TP completo debe ejecutar venta total."""
        em, portfolio, exchange, notifier = self._make_exit_manager()
        trade = make_trade(entry_price=1000.0, amount_usd=100.0)
        portfolio.get_open_trades.return_value = [trade]

        # Precio sube 6% → TP=5% activado
        current_price = 1000.0 * 1.06
        exchange.fetch_ticker.return_value = current_price
        exchange.get_balance.return_value = {"ETH": 0.1}
        exchange.create_market_sell_order.return_value = {"status": "closed"}

        await em.check_open_positions()

        exchange.create_market_sell_order.assert_called_once()
        portfolio.close_trade.assert_called_once_with(trade.id, current_price)

    @pytest.mark.asyncio
    async def test_stop_loss_triggers_full_sell(self):
        """Cuando el PnL cae al SL debe ejecutar venta total."""
        em, portfolio, exchange, notifier = self._make_exit_manager()
        trade = make_trade(entry_price=1000.0, amount_usd=100.0)
        portfolio.get_open_trades.return_value = [trade]

        # Precio baja 3% → SL=-2% activado
        current_price = 1000.0 * 0.97
        exchange.fetch_ticker.return_value = current_price
        exchange.get_balance.return_value = {"ETH": 0.1}
        exchange.create_market_sell_order.return_value = {"status": "closed"}

        await em.check_open_positions()

        exchange.create_market_sell_order.assert_called_once()
        portfolio.close_trade.assert_called_once_with(trade.id, current_price)

    @pytest.mark.asyncio
    async def test_partial_exit_at_half_tp(self):
        """Debe ejecutar salida parcial (50%) al alcanzar la mitad del TP."""
        em, portfolio, exchange, notifier = self._make_exit_manager()
        trade = make_trade(entry_price=1000.0, amount_usd=100.0)
        portfolio.get_open_trades.return_value = [trade]

        # Precio sube 2.5% = 50% del TP (5%)
        current_price = 1000.0 * 1.025
        exchange.fetch_ticker.return_value = current_price
        exchange.get_balance.return_value = {"ETH": 0.1}
        exchange.create_market_sell_order.return_value = {"status": "closed"}

        await em.check_open_positions()

        # Debe vender la mitad del balance
        exchange.create_market_sell_order.assert_called_once()
        args = exchange.create_market_sell_order.call_args[0]
        assert args[1] == pytest.approx(0.1 * 0.5, rel=1e-6)

        # NO debe cerrar el trade completamente
        portfolio.close_trade.assert_not_called()

    def test_trailing_stop_not_triggered_before_threshold(self):
        """El trailing stop NO debe activarse si el HWM no alcanzó el trigger."""
        em, _, _, _ = self._make_exit_manager()
        trade = make_trade(entry_price=1000.0)
        # PnL actual solo 1% < TRAILING_STOP_TRIGGER_PCT=3%
        action, reason, fraction = em._determine_exit_action(
            trade, pnl_pct=1.0, current_price=1010.0
        )
        assert action == "none"

    def test_trailing_stop_triggers_after_retrace(self):
        """El trailing stop debe activarse cuando el precio retrocede desde el HWM."""
        em, _, _, _ = self._make_exit_manager()
        trade = make_trade(entry_price=1000.0)

        # HWM en $1040 (4% de ganancia → > TRAILING_STOP_TRIGGER_PCT=3%)
        em._high_water_marks[trade.id] = 1040.0

        # Precio actual $1020 = retroceso de ≈1.92% desde $1040
        # TRAILING_STOP_DISTANCE_PCT=1.5% → debería activarse
        action, reason, fraction = em._determine_exit_action(
            trade, pnl_pct=2.0, current_price=1020.0
        )
        assert action == "full"
        assert "TRAILING STOP" in reason

    def test_update_high_water_mark(self):
        """El HWM solo debe actualizarse con precios superiores al anterior."""
        em, _, _, _ = self._make_exit_manager()
        em._update_high_water_mark(1, 1000.0)
        em._update_high_water_mark(1, 1100.0)
        em._update_high_water_mark(1, 950.0)  # No debe bajar el HWM
        assert em._high_water_marks[1] == 1100.0


# ═══════════════════════════════════════════════════════════════════════════ #
#  PORTFOLIO SERVICE TESTS (con mocks de DB)
# ═══════════════════════════════════════════════════════════════════════════ #

class TestPortfolioService:
    """Tests del PortfolioService usando mocks de las sesiones SQLAlchemy."""

    @pytest.mark.asyncio
    async def test_get_open_trades_returns_empty_on_error(self):
        """Si la DB falla, get_open_trades debe retornar lista vacía."""
        ps = PortfolioService.__new__(PortfolioService)
        ps._session_factory = MagicMock(side_effect=RuntimeError("DB error"))

        result = await ps.get_open_trades()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_daily_pnl_returns_zero_on_error(self):
        """Si la DB falla, get_daily_pnl debe retornar 0.0."""
        ps = PortfolioService.__new__(PortfolioService)
        ps._session_factory = MagicMock(side_effect=RuntimeError("DB error"))

        result = await ps.get_daily_pnl()
        assert result == 0.0

    def test_trade_dto_from_db_model(self):
        """Trade.from_db debe mapear correctamente los campos del ORM."""
        from app.models.db_models import Trade as DBTrade
        db_trade = DBTrade()
        db_trade.id = 42
        db_trade.token_symbol = "SOL"
        db_trade.entry_price = 200.0
        db_trade.amount_usd = 150.0
        db_trade.status = "OPEN"
        db_trade.exit_price = None
        db_trade.created_at = datetime.now(timezone.utc)

        trade = Trade.from_db(db_trade)
        assert trade.id == 42
        assert trade.token_symbol == "SOL"
        assert trade.entry_price == 200.0
        assert trade.exit_price is None
