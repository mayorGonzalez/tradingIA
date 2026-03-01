"""
Portfolio Service - Gestión de posiciones de trading
=====================================================
"""

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, time, timezone
from app.models.db_models import Trade, TradeStatus
from app.infraestructure.database import async_session_factory
from typing import List, Optional
from loguru import logger


# Mock de Trade para testing
class Trade:
    def __init__(self, token_symbol: str, entry_price: float, amount_usd: float, 
                 status: str = "OPEN", entry_date: Optional[datetime] = None):
        self.token_symbol = token_symbol
        self.entry_price = entry_price
        self.amount_usd = amount_usd
        self.status = status
        self.entry_date = entry_date or datetime.now()
        self.pnl_pct = 0.0


class PortfolioService:
    """Servicio de gestión del portfolio."""
    
    def __init__(self):
        #self.session_factory = async_session_factory
         # Mock: Simular trades abiertos
        self.mock_trades: List[Trade] = []
        logger.info("✓ PortfolioService initializado")

    async def get_open_trades(self) -> List[Trade]:
        """Obtener trades abiertos."""
        try:
            # En producción, esto consultaría la BD
            # Por ahora, retorna mock data
            return self.mock_trades
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []

    async def save_trade(self, token_symbol: str, entry_price: float, amount_usd: float) -> bool:
        """Guardar un nuevo trade."""
        try:
            trade = Trade(
                token_symbol=token_symbol,
                entry_price=entry_price,
                amount_usd=amount_usd
            )
            self.mock_trades.append(trade)
            logger.info(f"✓ Trade guardado: {token_symbol} @ ${entry_price} ({amount_usd}$)")
            return True
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False

    async def close_trade(self, trade_id: str, exit_price: float) -> bool:
        """Cerrar un trade."""
        try:
            # En producción, actualizar la BD
            logger.info(f"✓ Trade cerrado: {trade_id} @ ${exit_price}")
            return True
        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return False
    
    async def get_portfolio_stats(self) -> dict:
        """Obtener estadísticas del portfolio."""
        try:
            total_invested = sum(t.amount_usd for t in self.mock_trades if t.status == "OPEN")
            return {
                'total_invested': total_invested,
                'open_trades': len([t for t in self.mock_trades if t.status == "OPEN"]),
                'closed_trades': len([t for t in self.mock_trades if t.status == "CLOSED"]),
            }
        except Exception as e:
            logger.error(f"Error getting portfolio stats: {e}")
            return {}

    # async def get_open_trades(self) -> List[Trade]:
    #     """Recupera todos los trades que aún están abiertos."""
    #     async with self.session_factory() as session:
    #         result = await session.execute(
    #             select(Trade).where(Trade.status == TradeStatus.OPEN.value)
    #         )
    #         return list(result.scalars().all())

    # async def close_trade(self, trade_id: int, exit_price: float) -> Optional[Trade]:
    #     """Actualiza el estado de un trade a CERRADO y registra el precio de salida."""
    #     async with self.session_factory() as session:
    #         async with session.begin():
    #             result = await session.execute(
    #                 select(Trade).where(Trade.id == trade_id)
    #             )
    #             trade = result.scalar_one_or_none()
                
    #             if trade:
    #                 trade.status = TradeStatus.CLOSED.value
    #                 trade.exit_price = exit_price
                    
    #                 # Calcular PnL para el log
    #                 profit = (exit_price - trade.entry_price) * (trade.amount_usd / trade.entry_price)
    #                 logger.success(f"Trade cerrado: {trade.token_symbol} ID:{trade_id} | Beneficio: ${profit:.2f}")
    #                 return trade
                
    #             logger.warning(f"No se encontró el trade ID:{trade_id} para cerrar.")
    #             return None

    # async def get_all_trades(self) -> List[Trade]:
    #     """Recupera el historial completo de trades."""
    #     async with self.session_factory() as session:
    #         result = await session.execute(
    #             select(Trade).order_by(Trade.created_at.desc())
    #         )
    #         return list(result.scalars().all())

    # async def check_persistence(self, symbol: str) -> bool:
    #     """Verifica si el token ha tenido actividad reciente en la DB."""
    #     async with self.session_factory() as session:
    #         result = await session.execute(
    #             select(Trade).where(Trade.token_symbol == symbol).limit(1)
    #         )
    #         return result.scalar_one_or_none() is not None

    # async def get_daily_pnl(self) -> float:
    #     """Calcula el PnL total acumulado de todos los trades cerrados hoy."""
    #     async with self.session_factory() as session:
    #         # Rango de tiempo: desde el inicio del día actual (UTC)
    #         today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
    #         # Buscamos todos los trades cerrados hoy
    #         result = await session.execute(
    #             select(Trade).where(
    #                 and_(
    #                     Trade.status == TradeStatus.CLOSED.value,
    #                     Trade.updated_at >= today_start
    #                 )
    #             )
    #         )
    #         closed_trades = result.scalars().all()
            
    #         total_pnl = 0.0
    #         for t in closed_trades:
    #             # PnL = (PrecioSalida - PrecioEntrada) * CantidadBase
    #             if t.exit_price:
    #                 base_amount = t.amount_usd / t.entry_price
    #                 total_pnl += (t.exit_price - t.entry_price) * base_amount
            
    #         return total_pnl
