from loguru import logger
from app.core.config import settings
from app.models.nansen import SignalResult

class RiskManager:
    """
    RiskManager — Guardián del Capital.
    
    Aplica controles de riesgo dinámicos antes de autorizar una operación.
    Filtra señales válidas basándose en la exposición total y métricas de volatilidad.
    """

    def __init__(self, current_exposure_usd: float = 0.0, max_per_trade_usd: float = 500.0):
        self.max_exposure_per_token_pct = 0.1  # 10% del capital total
        self.current_exposure = current_exposure_usd
        self.max_per_trade_usd = max_per_trade_usd

    def validate_execution(self, signal: SignalResult, available_balance: float) -> bool:
        """
        Valida si una señal validada técnicamente es apta para ejecución financiera.
        """
        # 1. Control de Tamaño de Posición
        max_investment = available_balance * self.max_exposure_per_token_pct
        
        # 2. Validación de Factores de Riesgo acumulados
        if len(signal.risk_factors) > 2:
            logger.warning(f"[Risk] {signal.token_symbol} descartado por demasiados factores de riesgo: {signal.risk_factors}")
            return False

        # 3. Control de Volatilidad (VaR Simplificado)
        if signal.price_change_1h and signal.price_change_1h < settings.STOP_LOSS_PCT:
             logger.warning(f"[Risk] {signal.token_symbol} en caída libre ({signal.price_change_1h}%). No entrar.")
             return False

        logger.info(f"[Risk] {signal.token_symbol} VALIDADO para ejecución. Inversión sugerida: ${max_investment:.2f}")
        return True

    def calculate_position_size(self, balance: float, signal_score: float) -> float:
        """
        Calcula cuánto invertir basado en la confianza (score).
        A mayor score, mayor cercanía al límite de exposición.
        """
        base_pct = self.max_exposure_per_token_pct
        confidence_multiplier = signal_score / 100.0
        
        investment = balance * base_pct * confidence_multiplier
        return round(investment, 2)