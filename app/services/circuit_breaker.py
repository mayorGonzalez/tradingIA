# app/services/circuit_breaker.py
from loguru import logger
from app.services.portfolio_service import PortfolioService
from app.core.config import settings

class CircuitBreaker:
    """
    CircuitBreaker — Sistema de Parada de Emergencia.
    
    Monitorea el estado general del portfolio para prevenir una espiral de pérdidas.
    Si el drawdown diario o el límite de posiciones se alcanza, bloquea nuevas aperturas.
    """
    def __init__(self, max_daily_drawdown_pct: float = None, max_open_trades: int = None):
        self.max_daily_drawdown_pct = max_daily_drawdown_pct or settings.MAX_DAILY_DRAWDOWN_PCT
        self.max_open_trades = max_open_trades or settings.MAX_OPEN_TRADES

    async def is_open(self, portfolio: PortfolioService, current_balance_usd: float) -> bool:
        """
        Evalúa si el circuito debe abrirse (detener el bot).
        Retorna True si la operación está prohibida.
        """
        try:
            # 1. Verificar número de posiciones abiertas
            open_trades = await portfolio.get_open_trades()
            if len(open_trades) >= self.max_open_trades:
                logger.warning(f"[CircuitBreaker] LÍMITE ALCANZADO: {len(open_trades)}/{self.max_open_trades} posiciones abiertas.")
                return True

            # 2. Verificar Drawdown Diario
            daily_pnl = await portfolio.get_daily_pnl()
            
            # Calculamos el umbral de pérdida en USD basado en el balance actual
            # (Aproximación simple: pérdida relativa al balance desplegado + disponible)
            drawdown_threshold_usd = -(current_balance_usd * self.max_daily_drawdown_pct / 100)
            
            if daily_pnl < drawdown_threshold_usd:
                logger.critical(
                    f"[CircuitBreaker] 🔴 ALERTA DE DRAWDOWN: PnL diario (${daily_pnl:,.2f}) "
                    f"supera el límite del {self.max_daily_drawdown_pct}% (${drawdown_threshold_usd:,.2f})."
                )
                return True

            logger.debug(f"[CircuitBreaker] Salud del portfolio OK. PnL Diario: ${daily_pnl:,.2f}")
            return False

        except Exception as e:
            logger.error(f"[CircuitBreaker] Error al evaluar estado: {e}")
            # En caso de error, abrimos el circuito por seguridad
            return True
