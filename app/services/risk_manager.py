from loguru import logger

class RiskManager:
    def __init__(self, max_per_trade_usd: float = 500.0, min_balance_safety: float = 100.0) -> None:
        self.max_per_trade_usd = max_per_trade_usd
        self.min_balance_safety = min_balance_safety

    def calculate_position_size(self, current_balance_usd: float) -> float:
        """Calcula cuánto invertir sin poner en riesgo la cuenta."""
        if current_balance_usd < self.min_balance_safety:
            logger.warning("Balance demasiado bajo para operar con seguridad.")
            return 0.0
        
        # Invertimos el máximo permitido o el 10% del balance (lo que sea menor)
        suggested = min(self.max_per_trade_usd, current_balance_usd * 0.10)
        return suggested