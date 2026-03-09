"""
RiskManager — Guardián del Capital
====================================
Aplica controles de riesgo dinámicos antes de autorizar una operación.
Filtra señales válidas basándose en:
  - Exposición total de la cartera
  - Tamaño de posición mínimo y máximo
  - Número de factores de riesgo en la señal
  - Volatilidad reciente del token (VaR simplificado)
  - Correlación implícita evitando re-entradas al mismo token
"""

from loguru import logger
from typing import List
from app.core.config import settings
from app.models.nansen import SignalResult

'''Este archivo es el "Guardián" o el "Filtro de Seguridad" de tu bot.

Imagina que tu cerebro (AIAnalyst) es un estratega brillante pero a veces impulsivo.
Este módulo es el "Contralor" que se sienta a su lado.

Su trabajo es decir:
- "Espera, cerebro. Esa señal parece buena, pero ¿tenemos suficiente dinero?"
- "¿Ya invertimos mucho en esta moneda? No podemos poner todos los huevos en la misma canasta."
- "¿Esta moneda está cayendo en picado ahora mismo? Mejor no comprar."

Es el encargado de proteger tu dinero real.'''

class RiskManager:
    """
    Controla el riesgo de cada operación antes de su ejecución en el exchange.

    Parámetros clave:
        max_exposure_per_token_pct: Porcentaje máximo del capital total invertible
                                    en un único token (por defecto 10%).
        current_exposure_usd:       Suma de USD actualmente desplegada en trades abiertos.
        max_per_trade_usd:          Cap absoluto en USD por operación (configurable).
    """

    def __init__(
        self,
        current_exposure_usd: float = 0.0,
        max_per_trade_usd: float | None = None,
    ):
        self.max_exposure_per_token_pct: float = 0.10   # 10% del capital total
        self.current_exposure: float = current_exposure_usd
        # Respetar config global si no se pasa explícitamente
        self.max_per_trade_usd: float = (
            max_per_trade_usd if max_per_trade_usd is not None
            else settings.MAX_POSITION_SIZE_USD
        )
        # Registro de tokens ya operados en este ciclo para control de correlación
        self._traded_symbols_this_cycle: List[str] = []

    # ------------------------------------------------------------------ #
    # Validación de ejecución
    # ------------------------------------------------------------------ #

    def validate_execution(self, signal: SignalResult, available_balance: float) -> bool:
        """
        Valida si una señal técnica es apta para ejecución financiera.

        Comprobaciones realizadas (en orden de coste computacional):
          1. Tamaño mínimo de posición — no abrir trades inviables por fees.
          2. Tamaño máximo de posición — limita el riesgo absoluto por trade.
          3. Exposición notional por token — evita concentrar más del 10% en un token.
          4. Factores de riesgo acumulados — demasiadas señales negativas en la señal.
          5. Volatilidad ajustada (VaR simplificado) — no entrar en caídas libres.
          6. Control de re-entrada / correlación implícita dentro del mismo ciclo.

        Args:
            signal:            Señal procesada por el SignalEngine.
            available_balance: USDT disponible en la cartera en este momento.

        Returns:
            True si la operación puede ejecutarse, False en caso contrario.
        """
        symbol = signal.token_symbol

        # --- 1. Tamaño mínimo viable ----------------------------------- #
        min_viable = settings.MIN_POSITION_SIZE_USD
        max_investment = available_balance * self.max_exposure_per_token_pct
        if max_investment < min_viable:
            logger.warning(
                f"[Risk] {symbol} rechazado: inversión calculada "
                f"(${max_investment:.2f}) < mínimo (${min_viable:.2f}). "
                f"Balance insuficiente."
            )
            return False

        # --- 2. Tamaño máximo por trade -------------------------------- #
        if self.max_per_trade_usd < min_viable:
            logger.warning(
                f"[Risk] {symbol} rechazado: MAX_POSITION_SIZE_USD "
                f"(${self.max_per_trade_usd}) está por debajo del mínimo operativo."
            )
            return False

        # --- 3. Exposición notional por token (anti-concentración) ----- #
        exposure_limit_usd = available_balance * self.max_exposure_per_token_pct
        if self.current_exposure + exposure_limit_usd > available_balance * 0.8:
            logger.warning(
                f"[Risk] {symbol} rechazado: exposición total "
                f"(${self.current_exposure:.2f}) + nueva posición superaría "
                f"el 80% del balance disponible."
            )
            return False

        # --- 4. Factores de riesgo acumulados -------------------------- #
        max_risk_factors = 2
        if len(signal.risk_factors) > max_risk_factors:
            logger.warning(
                f"[Risk] {symbol} descartado por demasiados factores de riesgo "
                f"({len(signal.risk_factors)}/{max_risk_factors}): {signal.risk_factors}"
            )
            return False

        # --- 5. Control de Volatilidad (VaR Simplificado) -------------- #
        if signal.price_change_1h is not None:
            if signal.price_change_1h < settings.STOP_LOSS_PCT:
                logger.warning(
                    f"[Risk] {symbol} en caída libre "
                    f"({signal.price_change_1h:+.2f}% en 1h). No entrar."
                )
                return False
            if signal.price_change_1h > settings.MAX_PRICE_CHANGE_1H_PCT:
                logger.warning(
                    f"[Risk] {symbol} en alza explosiva (FOMO) "
                    f"({signal.price_change_1h:+.2f}% en 1h > límite "
                    f"{settings.MAX_PRICE_CHANGE_1H_PCT}%). No entrar."
                )
                return False

        # --- 6. Correlación / Re-entrada en el mismo ciclo ------------- #
        if symbol in self._traded_symbols_this_cycle:
            logger.warning(
                f"[Risk] {symbol} ya fue operado en este ciclo. "
                f"Evitando re-entrada para reducir correlación."
            )
            return False

        logger.info(
            f"[Risk] ✅ {symbol} VALIDADO para ejecución. "
            f"Inversión máxima sugerida: ${min(max_investment, self.max_per_trade_usd):.2f}"
        )
        return True

    # ------------------------------------------------------------------ #
    # Cálculo del tamaño de posición
    # ------------------------------------------------------------------ #

    def calculate_position_size(self, balance: float, signal_score: float) -> float:
        """
        Calcula cuánto invertir basado en el balance y la confianza de la señal.

        Fórmula:
            position = balance × max_exposure_pct × (score / 100)

        El resultado se acota entre MIN_POSITION_SIZE_USD y MAX_POSITION_SIZE_USD
        para garantizar que la posición siempre sea viable y nunca exceda el cap.

        Args:
            balance:      USDT disponible.
            signal_score: Score de la señal (0–100).

        Returns:
            Monto en USD a invertir, redondeado a 2 decimales.
        """
        confidence_multiplier = max(0.0, min(signal_score / 100.0, 1.0))
        raw_investment = balance * self.max_exposure_per_token_pct * confidence_multiplier

        # Ajustar por volatilidad implícita en el score:
        # scores bajos → reducir tamaño adicionalmente un 50%
        if signal_score < 50:
            raw_investment *= 0.5
            logger.debug(
                f"[Risk] Score bajo ({signal_score}): reduciendo posición "
                f"un 50% → ${raw_investment:.2f}"
            )

        # Acotar entre mínimo y máximo definidos en configuración
        position = max(settings.MIN_POSITION_SIZE_USD, min(raw_investment, self.max_per_trade_usd))
        return round(position, 2)

    # ------------------------------------------------------------------ #
    # Control del ciclo
    # ------------------------------------------------------------------ #

    def register_trade(self, symbol: str, amount_usd: float) -> None:
        """
        Registra que se ha ejecutado un trade en este ciclo.
        Debe llamarse después de una compra exitosa para actualizar
        la exposición actual y el historial del ciclo.

        Args:
            symbol:     Ticker del token comprado (ej. "BTC").
            amount_usd: Monto en USD invertido.
        """
        self._traded_symbols_this_cycle.append(symbol)
        self.current_exposure += amount_usd
        logger.debug(
            f"[Risk] Trade registrado: {symbol} +${amount_usd:.2f} | "
            f"Exposición total: ${self.current_exposure:.2f}"
        )

    def reset_cycle(self) -> None:
        """
        Reinicia el estado del ciclo al comienzo de cada iteración del bot.
        Limpia el historial de símbolos operados para el control de correlación.
        La exposición actual NO se resetea aquí; debe obtenerse del portfolio real.
        """
        self._traded_symbols_this_cycle.clear()
        logger.debug("[Risk] Estado del ciclo reiniciado.")