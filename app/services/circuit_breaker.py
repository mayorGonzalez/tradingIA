"""
CircuitBreaker — Sistema de Parada de Emergencia
================================================
Monitorea el estado general del portfolio para prevenir una espiral de pérdidas.

Condiciones que ABREN el circuito (bloquean nuevas operaciones):
  1. Límite de posiciones simultáneas alcanzado (MAX_OPEN_TRADES).
  2. Drawdown diario supera el umbral configurado (MAX_DAILY_DRAWDOWN_PCT).
  3. Error inesperado al consultar el portfolio (falla por defecto → seguro).

Cálculo de Drawdown:
    drawdown_threshold_usd = -(usdt_balance × MAX_DAILY_DRAWDOWN_PCT / 100)
    Si daily_pnl < drawdown_threshold_usd → circuito abierto.

    Ejemplo: balance=10.000$, MAX_DAILY_DRAWDOWN_PCT=5
    → Límite = -500$. Si el bot pierde >500$ en el día, se detiene.

Duración del bloqueo:
    El circuito permanece abierto durante CIRCUIT_BREAK_DURATION_MINUTES (por
    defecto 60 min) para evitar re-activación inmediata del bot en el mismo ciclo.
    Solo una instancia nueva del bot (o reinicio) resetea el temporizador.

Parámetros configurables (ver app/core/config.py):
    MAX_DAILY_DRAWDOWN_PCT       — % máximo de pérdida sobre balance disponible
    MAX_OPEN_TRADES              — número máximo de posiciones abiertas en paralelo
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
        if await breaker.is_open(portfolio, usdt_balance):
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

        # Estado interno del breaker
        self._tripped_at: datetime | None = None  # Momento en que se activó el breaker
        self._trip_reason: str = ""               # Motivo del activado (para logs)

    # ------------------------------------------------------------------ #
    # Interfaz pública
    # ------------------------------------------------------------------ #

    async def is_open(self, portfolio: PortfolioService, current_balance_usd: float) -> bool:
        """
        Evalúa si el circuito está abierto (operaciones prohibidas).

        Flujo de evaluación:
          1. Si el breaker ya fue activado anteriormente, comprobar si aún
             está dentro de la ventana de bloqueo (break_duration).
          2. Comprobar el número de posiciones abiertas vs MAX_OPEN_TRADES.
          3. Comprobar el PnL diario vs el umbral de drawdown.
          4. Ante cualquier excepción → abrir el circuito por seguridad.

        Args:
            portfolio:           Instancia del servicio de portfolio.
            current_balance_usd: Balance USDT disponible actualmente.

        Returns:
            True  → circuito ABIERTO, NO operar.
            False → circuito CERRADO, OK para operar.
        """
        # --- Fase 0: ¿Sigue activo un bloqueo previo? ------------------ #
        if self._is_still_tripped():
            remaining = self._remaining_block_time()
            logger.warning(
                f"[CircuitBreaker] 🔴 Circuito abierto (motivo: {self._trip_reason}). "
                f"Tiempo restante de bloqueo: {remaining:.1f} min."
            )
            return True

        try:
            # --- Fase 1: Límite de posiciones abiertas ------------------ #
            open_trades = await portfolio.get_open_trades()
            if len(open_trades) >= self.max_open_trades:
                self._trip(
                    reason=f"Límite de posiciones alcanzado "
                    f"({len(open_trades)}/{self.max_open_trades})"
                )
                logger.warning(f"[CircuitBreaker] {self._trip_reason}")
                return True

            # --- Fase 2: Drawdown diario -------------------------------- #
            daily_pnl = await portfolio.get_daily_pnl()

            # Umbral de pérdida en USD: p.ej. -5% de 10.000$ = -500$
            drawdown_threshold_usd = -(
                current_balance_usd * self.max_daily_drawdown_pct / 100.0
            )

            if daily_pnl < drawdown_threshold_usd:
                self._trip(
                    reason=(
                        f"Drawdown diario excedido: "
                        f"PnL=${daily_pnl:,.2f} < "
                        f"límite=${drawdown_threshold_usd:,.2f} "
                        f"({self.max_daily_drawdown_pct}% de ${current_balance_usd:,.2f})"
                    )
                )
                logger.critical(f"[CircuitBreaker] 🔴 ALERTA DRAWDOWN: {self._trip_reason}")
                return True

            # --- Salud OK ---------------------------------------------- #
            logger.debug(
                f"[CircuitBreaker] ✅ Portfolio saludable. "
                f"Posiciones: {len(open_trades)}/{self.max_open_trades} | "
                f"PnL Diario: ${daily_pnl:,.2f} (límite: ${drawdown_threshold_usd:,.2f})"
            )
            return False

        except Exception as exc:
            logger.error(
                f"[CircuitBreaker] Error al evaluar estado del portfolio: {exc}. "
                f"Abriendo circuito por seguridad."
            )
            self._trip(reason=f"Error interno: {exc}")
            return True

    def reset(self) -> None:
        """
        Resetea manualmente el estado del breaker.
        Usar con precaución: solo en operaciones de mantenimiento o tests.
        """
        self._tripped_at = None
        self._trip_reason = ""
        logger.info("[CircuitBreaker] Circuito reseteado manualmente.")

    # ------------------------------------------------------------------ #
    # Métodos privados
    # ------------------------------------------------------------------ #

    def _trip(self, reason: str) -> None:
        """Activa el circuito y registra el momento y motivo."""
        self._tripped_at = datetime.now(timezone.utc)
        self._trip_reason = reason

    def _is_still_tripped(self) -> bool:
        """Verdadero si el circuito fue activado y aún no expiró la ventana de bloqueo."""
        if self._tripped_at is None:
            return False
        elapsed = datetime.now(timezone.utc) - self._tripped_at
        return elapsed < self.break_duration

    def _remaining_block_time(self) -> float:
        """Devuelve los minutos restantes de bloqueo (0 si el circuito ya expiró)."""
        if self._tripped_at is None:
            return 0.0
        elapsed = datetime.now(timezone.utc) - self._tripped_at
        remaining = self.break_duration - elapsed
        return max(0.0, remaining.total_seconds() / 60.0)
