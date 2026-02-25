from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Trade, TradeStatus
from app.infraestructure.database import async_session_factory
from typing import List, Optional
from loguru import logger

class PortfolioService:
    def __init__(self) -> None:
        self.session_factory = async_session_factory

    async def save_trade(self, symbol: str, price: float, amount: float) -> Trade:
        """Registra una nueva compra en la base de datos."""
        async with self.session_factory() as session:
            async with session.begin():
                new_trade = Trade(
                    token_symbol=symbol,
                    entry_price=price,
                    amount_usd=amount,
                    status=TradeStatus.OPEN.value
                )
                session.add(new_trade)
            
            await session.refresh(new_trade)
            logger.info(f"Trade guardado: {symbol} a ${price}")
            return new_trade

    async def get_open_trades(self) -> List[Trade]:
        """Recupera todos los trades que aún están abiertos."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.OPEN.value)
            )
            return list(result.scalars().all())

    async def close_trade(self, trade_id: int, exit_price: float) -> Optional[Trade]:
        """Actualiza el estado de un trade a CERRADO y registra el precio de salida."""
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Trade).where(Trade.id == trade_id)
                )
                trade = result.scalar_one_or_none()
                
                if trade:
                    trade.status = TradeStatus.CLOSED.value
                    trade.exit_price = exit_price
                    
                    # Calcular PnL para el log
                    profit = (exit_price - trade.entry_price) * (trade.amount_usd / trade.entry_price)
                    logger.success(f"Trade cerrado: {trade.token_symbol} ID:{trade_id} | Beneficio: ${profit:.2f}")
                    return trade
                
                logger.warning(f"No se encontró el trade ID:{trade_id} para cerrar.")
                return None

    async def get_all_trades(self) -> List[Trade]:
        """Recupera el historial completo de trades."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Trade).order_by(Trade.created_at.desc())
            )
            return list(result.scalars().all())

    async def check_persistence(self, symbol: str) -> bool:
        """Verifica si el token ha tenido actividad reciente en la DB."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Trade).where(Trade.token_symbol == symbol).limit(1)
            )
            return result.scalar_one_or_none() is not None
