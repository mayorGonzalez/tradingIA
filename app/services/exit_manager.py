"""
ExitManager — Gestión de Salidas de Posiciones
===============================================
Monitoriza posiciones abiertas y ejecuta órdenes de venta según reglas de:
  - Take Profit (TP): cierre completo cuando PnL >= TAKE_PROFIT_PCT
  - Stop Loss (SL):   cierre completo cuando PnL <= STOP_LOSS_PCT
  - Trailing Stop:    activa cuando PnL >= TRAILING_STOP_TRIGGER_PCT y luego
                      cierra si el precio retrocede TRAILING_STOP_DISTANCE_PCT
                      desde el máximo registrado.
  - Partial Exit:     vende el 50% de la posición al alcanzar el 50% del TP,
                      asegurando ganancias parciales antes del TP completo.

Flujo por posición:
  1. Obtener precio actual del exchange.
  2. Calcular PnL porcentual vs precio de entrada.
  3. Actualizar high-water mark interna (trailing stop).
  4. Evaluar reglas de salida en orden de prioridad:
       SL → Trailing Stop → Partial Exit → TP.
  5. Ejecutar orden de venta (total o parcial).
  6. Actualizar DB y enviar notificación Telegram.
"""

from __future__ import annotations

from loguru import logger
from app.core.config import settings
from app.infraestructure.exchange_client import ExchangeClient
from app.services.portfolio_service import PortfolioService, Trade
from app.services.notifier import TelegramNotifier


class ExitManager:
    """
    Gestiona salidas automáticas de posiciones abiertas.

    Atributos internos:
        _high_water_marks: dict[int, float]
            Precio máximo registrado por trade_id desde su apertura.
            Se usa para el cálculo del trailing stop.
        _partial_exits_done: set[int]
            IDs de trades donde ya se ejecutó una salida parcial.
            Evita ejecutar múltiples salidas parciales en el mismo trade.
    """

    def __init__(
        self,
        portfolio_service: PortfolioService,
        exchange_client: ExchangeClient,
        notifier: TelegramNotifier,
    ) -> None:
        self.portfolio_service = portfolio_service
        self.exchange_client = exchange_client
        self.notifier = notifier

        # Estado interno del trailing stop y partial exits
        self._high_water_marks: dict[int, float] = {}
        self._partial_exits_done: set[int] = set()

    # ------------------------------------------------------------------ #
    # Punto de entrada principal
    # ------------------------------------------------------------------ #

    async def check_open_positions(self) -> None:
        """
        Itera sobre todas las posiciones abiertas y evalúa reglas de salida.
        Debe llamarse en cada ciclo del bot ANTES de buscar nuevas señales.
        """
        logger.info("[Exit] Chequeando posiciones abiertas para posibles salidas...")
        open_trades = await self.portfolio_service.get_open_trades()

        if not open_trades:
            logger.info("[Exit] No hay posiciones abiertas actualmente.")
            return

        for trade in open_trades:
            try:
                # Recuperar estado de la DB si no está en RAM
                if trade.id not in self._high_water_marks:
                    self._high_water_marks[trade.id] = trade.entry_price
                
                await self._evaluate_trade(trade)
            except Exception as exc:
                logger.error(f"[Exit] Fallo crítico en trade {trade.token_symbol}: {exc}")
    # ------------------------------------------------------------------ #
    # Evaluación individual de un trade
    # ------------------------------------------------------------------ #

    async def _evaluate_trade(self, trade: Trade) -> None:
        """
        Evalúa un trade individual y ejecuta la acción de salida si aplica.

        Args:
            trade: Trade abierto a evaluar.
        """
        symbol = trade.token_symbol
        current_price = await self.exchange_client.fetch_ticker(symbol)

        if current_price is None:
            logger.warning(f"[Exit] No se pudo obtener precio de {symbol}. Saltando.")
            return

        # Calcular PnL porcentual
        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
        logger.debug(f"[Exit] {symbol}: PnL={pnl_pct:+.2f}% | Precio actual=${current_price:,.4f}")

        # Actualizar máximo histórico (High Water Mark)
        if current_price > self._high_water_marks.get(trade.id, 0):
            self._high_water_marks[trade.id] = current_price

        action, reason, sell_fraction = self._determine_exit_action(trade, pnl_pct, current_price)

        if action != "none":
            await self._execute_exit(trade, current_price, pnl_pct, reason, sell_fraction)
    # ------------------------------------------------------------------ #
    # Lógica de decisión
    # ------------------------------------------------------------------ #

    def _determine_exit_action(
        self,
        trade: Trade,
        pnl_pct: float,
        current_price: float,
    ) -> tuple[str, str, float]:
        """
        Determina si se debe salir de la posición y con qué fracción.

        Returns:
            Tupla (action, reason, sell_fraction) donde:
              - action:       "full" | "partial" | "none"
              - reason:       Descripción para logs/notificación
              - sell_fraction: Fracción del balance a vender (1.0=100%, 0.5=50%)
        """
        symbol = trade.token_symbol

        # --- Stop Loss (prioridad máxima) ------------------------------ #
        if pnl_pct <= settings.STOP_LOSS_PCT:
            return (
                "full",
                f"STOP LOSS ({settings.STOP_LOSS_PCT}%) — PnL: {pnl_pct:+.2f}%",
                1.0,
            )

        # --- Trailing Stop --------------------------------------------- #
        hwm = self._high_water_marks.get(trade.id, trade.entry_price)
        hwm_pnl_pct = ((hwm - trade.entry_price) / trade.entry_price) * 100

        if hwm_pnl_pct >= settings.TRAILING_STOP_TRIGGER_PCT:
            # El trailing stop se activa: revisar retroceso desde el máximo
            retrace_from_hwm_pct = ((current_price - hwm) / hwm) * 100
            if retrace_from_hwm_pct <= -settings.TRAILING_STOP_DISTANCE_PCT:
                return (
                    "full",
                    (
                        f"TRAILING STOP activado — Máximo: ${hwm:,.4f} "
                        f"({hwm_pnl_pct:+.2f}%) | Retroceso: {retrace_from_hwm_pct:.2f}% "
                        f"(≥ -{settings.TRAILING_STOP_DISTANCE_PCT}%)"
                    ),
                    1.0,
                )

        # --- Partial Exit (50% al alcanzar mitad del TP) --------------- #
        half_tp = settings.TAKE_PROFIT_PCT / 2.0
        if (
            pnl_pct >= half_tp
            and pnl_pct < settings.TAKE_PROFIT_PCT
            and trade.id not in self._partial_exits_done
        ):
            return (
                "partial",
                f"PARTIAL EXIT (50%) a {pnl_pct:+.2f}% (mitad del TP={settings.TAKE_PROFIT_PCT}%)",
                0.5,
            )

        # --- Take Profit completo -------------------------------------- #
        if pnl_pct >= settings.TAKE_PROFIT_PCT:
            return (
                "full",
                f"TAKE PROFIT ({settings.TAKE_PROFIT_PCT}%) — PnL: {pnl_pct:+.2f}%",
                1.0,
            )

        return "none", "", 0.0

    # ------------------------------------------------------------------ #
    # Ejecución en el exchange
    # ------------------------------------------------------------------ #

    async def _execute_exit(
        self,
        trade: Trade,
        current_price: float,
        pnl_pct: float,
        reason: str,
        sell_fraction: float,
    ) -> None:
        """
        Ejecuta la orden de venta (total o parcial) en el exchange.

        Args:
            trade:         Trade a cerrar o reducir.
            current_price: Precio actual del activo.
            pnl_pct:       PnL porcentual calculado.
            reason:        Motivo de la salida (para logs/notificación).
            sell_fraction: Fracción del balance a vender (1.0=100%, 0.5=50%).
        """
        symbol = trade.token_symbol
        is_partial = sell_fraction < 1.0

        logger.warning(
            f"[Exit] {'PARCIAL' if is_partial else 'TOTAL'} para {symbol}: {reason}"
        )

        # Obtener balance real del token en el exchange
        balances = await self.exchange_client.get_balance()
        token_base = symbol.split("/")[0] if "/" in symbol else symbol
        real_token_balance = (balances.get(token_base, 0.0) if balances else 0.0)

        if real_token_balance <= 0:
            # Fallback a estimación desde DB
            real_token_balance = trade.amount_usd / trade.entry_price
            logger.warning(
                f"[Exit] {symbol}: balance real=0. "
                f"Usando estimación DB: {real_token_balance:.6f} tokens"
            )

        amount_to_sell = round(real_token_balance * sell_fraction, 8)

        if amount_to_sell <= 0:
            logger.error(f"[Exit] {symbol}: cantidad a vender={amount_to_sell}. Abortando.")
            return

        # Ejecutar orden en el exchange
        order = await self.exchange_client.create_market_sell_order(symbol, amount_to_sell)

        if not order:
            logger.error(
                f"[Exit] {symbol}: La orden de venta falló. Se reintentará en el próximo ciclo."
            )
            return

        # Registrar en portfolio
        if is_partial:
            # Partial exit: no cerramos el trade, solo lo registramos
            self._partial_exits_done.add(trade.id)
            logger.success(
                f"[Exit] Salida parcial ejecutada: {symbol} | "
                f"Vendidos: {amount_to_sell:.6f} tokens | PnL: {pnl_pct:+.2f}%"
            )
        else:
            # Full exit: cerrar el trade en DB
            await self.portfolio_service.close_trade(trade.id, current_price)
            # Limpiar estado interno del trade
            self._high_water_marks.pop(trade.id, None)
            self._partial_exits_done.discard(trade.id)
            logger.success(
                f"[Exit] Posición cerrada: {symbol} @ ${current_price:,.4f} | PnL: {pnl_pct:+.2f}%"
            )

        # Notificación Telegram
        icon = "📉" if "STOP" in reason else ("⚡" if is_partial else "🏁")
        report = (
            f"{icon} <b>{'SALIDA PARCIAL' if is_partial else 'POSICIÓN CERRADA'}: {symbol}</b>\n"
            f"📌 Razón: {reason}\n"
            f"💰 PnL: <b>{pnl_pct:+.2f}%</b>\n"
            f"💵 Entrada: ${trade.entry_price:,.4f}\n"
            f"📉 Salida: ${current_price:,.4f}\n"
            f"🔢 Tokens vendidos: {amount_to_sell:.6f}"
        )
        await self.notifier.send_alert(report)

    # ------------------------------------------------------------------ #
    # Estado interno
    # ------------------------------------------------------------------ #

    def _update_high_water_mark(self, trade_id: int, current_price: float) -> None:
        """
        Actualiza el precio máximo histórico de un trade para el trailing stop.
        Solo actualiza si el precio actual supera el máximo registrado.
        """
        previous = self._high_water_marks.get(trade_id, 0.0)
        if current_price > previous:
            self._high_water_marks[trade_id] = current_price
