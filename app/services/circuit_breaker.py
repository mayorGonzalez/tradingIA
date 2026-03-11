"""
CircuitBreaker — Sistema de Parada de Emergencia
================================================
Monitorea el estado general del portfolio para prevenir una espiral de pérdidas.

Condiciones que ABREN el circuito (bloquean nuevas operaciones):
  1. Límite de posiciones simultáneas alcanzado (MAX_OPEN_TRADES).
  2. Drawdown diario supera el umbral configurado (MAX_DAILY_DRAWDOWN_PCT).
  3. Error inesperado al consultar el portfolio (falla por defecto → seguro).

Cálculo de Drawdown:
    drawdown_threshold_usd = total_equity × MAX_DAILY_DRAWDOWN_PCT / 100
    Si daily_pnl < -drawdown_threshold_usd → circuito abierto.

    Ejemplo: equity=10.000$, MAX_DAILY_DRAWDOWN_PCT=5
    → Límite = -500$. Si el bot pierde >500$ en el día, se detiene.

Duración del bloqueo:
    El circuito permanece abierto durante CIRCUIT_BREAK_DURATION_MINUTES (por
    defecto 60 min). Solo una instancia nueva del bot (o reinicio) resetea el
    temporizador.

Parámetros configurables (ver app/core/config.py):
    MAX_DAILY_DRAWDOWN_PCT         — % máximo de pérdida sobre equity total
    MAX_OPEN_TRADES                — número máximo de posiciones abiertas en paralelo
    CIRCUIT_BREAK_DURATION_MINUTES — duración del bloqueo tras activar el breaker
"""

from datetime import datetime, timedelta, timezone
from loguru import logger
from app.services.portfolio_service import PortfolioService
from app.core.config import settings


class CircuitBreaker:
    """
    Guardián de emergencia del bot de trading.

    Uso:
        breaker = CircuitBreaker()
        if await breaker.is_open(portfolio, total_equity):
            return  # NO operar
    """

    def __init__(
        self,
        max_daily_drawdown_pct: float | None = None,
        max_open_trades: int | None = None,
        break_duration_minutes: int | None = None,
    ):
        """
        Args:
            max_daily_drawdown_pct:   % máximo de pérdida diaria permitida.
                                      Si None, usa settings.MAX_DAILY_DRAWDOWN_PCT.
            max_open_trades:          Número máximo de posiciones abiertas.
                                      Si None, usa settings.MAX_OPEN_TRADES.
            break_duration_minutes:   Minutos que el circuito permanece abierto
                                      tras detectar un breach. Si None, usa
                                      settings.CIRCUIT_BREAK_DURATION_MINUTES.
        """
        self.max_daily_drawdown_pct: float = (
            max_daily_drawdown_pct
            if max_daily_drawdown_pct is not None
            else settings.MAX_DAILY_DRAWDOWN_PCT
        )
        self.max_open_trades: int = max_open_trades or settings.MAX_OPEN_TRADES
        self.break_duration: timedelta = timedelta(
            minutes=break_duration_minutes or settings.CIRCUIT_BREAK_DURATION_MINUTES
        )

        self._tripped_at: datetime | None = None
        self._trip_reason: str = ""
        # FIX: guardamos la fecha completa, no solo el día del mes,
        # para evitar falsos resets (ej. día 5 de enero vs día 5 de febrero)
        self._last_reset_date: datetime.date = datetime.now(timezone.utc).date()

    # ------------------------------------------------------------------ #
    # Interfaz pública
    # ------------------------------------------------------------------ #

    async def is_open(self, portfolio: PortfolioService, total_equity_usd: float) -> bool:
        """
        Evalúa el estado del circuito.

        Args:
            portfolio:        Instancia del servicio de portfolio.
            total_equity_usd: Equity total (Balance + PnL flotante de todas las chains).

        Returns:
            True si el circuito está abierto (NO operar), False si está cerrado (operar).
        """
        # FIX: comparar fecha completa (año+mes+día) en lugar de solo .day (1-31)
        current_date = datetime.now(timezone.utc).date()
        if current_date != self._last_reset_date:
            self.reset()
            self._last_reset_date = current_date

        if self._is_still_tripped():
            remaining = self._remaining_block_time()
            logger.warning(
                f"[CircuitBreaker] 🔴 BLOQUEADO. "
                f"Motivo: {self._trip_reason}. "
                f"Restan {int(remaining)} min."
            )
            return True

        try:
            # 1. Límite de posiciones simultáneas
            open_trades = await portfolio.get_open_trades()
            if len(open_trades) >= self.max_open_trades:
                self._trip(f"Capacidad máxima: {len(open_trades)} posiciones abiertas.")
                logger.warning(f"[CircuitBreaker] 🔴 {self._trip_reason}")
                return True

            # 2. Drawdown diario real
            # FIX: el límite se calcula sobre total_equity_usd, no sobre el balance USDT puro,
            # para reflejar el valor real de la cartera incluyendo posiciones abiertas.
            daily_pnl = await portfolio.get_daily_pnl()
            limit_usd = total_equity_usd * self.max_daily_drawdown_pct / 100.0

            if daily_pnl < 0 and abs(daily_pnl) > limit_usd:
                self._trip(
                    f"Drawdown superado: pérdida de ${abs(daily_pnl):,.0f} "
                    f"sobre límite de ${limit_usd:,.0f} "
                    f"({self.max_daily_drawdown_pct}% de equity)."
                )
                logger.critical(f"[CircuitBreaker] 🔴 STOP OPERATIVO: {self._trip_reason}")
                return True

            return False

        except Exception as exc:
            # Fail-safe: ante cualquier error en los sensores, bloqueamos operaciones
            self._trip(f"Fallo en sensor de portfolio: {exc}")
            logger.error(f"[CircuitBreaker] 🔴 Error inesperado, circuito abierto: {exc}")
            return True

    # ------------------------------------------------------------------ #
    # Métodos privados
    # ------------------------------------------------------------------ #

    def _trip(self, reason: str) -> None:
        """Activa el circuito y registra el momento y motivo."""
        self._tripped_at = datetime.now(timezone.utc)
        self._trip_reason = reason

    def _is_still_tripped(self) -> bool:
        """Devuelve True si el circuito sigue activo (dentro del periodo de bloqueo)."""
        if self._tripped_at is None:
            return False
        return (datetime.now(timezone.utc) - self._tripped_at) < self.break_duration

    def _remaining_block_time(self) -> float:
        """Devuelve los minutos restantes de bloqueo. 0.0 si el circuito ya expiró."""
        if self._tripped_at is None:
            return 0.0
        elapsed = datetime.now(timezone.utc) - self._tripped_at
        remaining = self.break_duration - elapsed
        return max(0.0, remaining.total_seconds() / 60.0)

    # ------------------------------------------------------------------ #
    # Gestión manual
    # ------------------------------------------------------------------ #

    def reset(self) -> None:
        """
        Resetea manualmente el estado del breaker.
        Se llama automáticamente al detectar un nuevo día.
        Usar con precaución en producción: solo para mantenimiento o tests.
        """
        self._tripped_at = None
        self._trip_reason = ""
        logger.info("[CircuitBreaker] ✅ Circuito reseteado.")