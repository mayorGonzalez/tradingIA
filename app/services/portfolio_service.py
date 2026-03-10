"""
PortfolioService — Gestión de Posiciones de Trading
=====================================================
Actúa como capa de abstracción sobre la base de datos SQLite.

Estado actual:
  - get_open_trades / save_trade / close_trade → usan DB real (SQLite async)
  - get_daily_pnl                              → usa DB real
  - check_persistence                          → usa DB real
  - get_portfolio_stats                        → calcula sobre DB

La clase Trade local es un DTO de presentación con atributo `id` necesario
para referencias en ExitManager y CircuitBreaker.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, select

from app.infraestructure.database import async_session_factory
from app.models.db_models import Trade as DBTrade, TradeStatus


# --------------------------------------------------------------------------- #
# DTO de presentación (desacoplado del modelo ORM)
# --------------------------------------------------------------------------- #

class Trade:
    """Data Transfer Object de un trade, compatible con ExitManager y CircuitBreaker."""

    def __init__(
        self,
        id: int,
        token_symbol: str,
        token_address: str, # Fundamental para DEX
        chain: str,
        entry_price: float,
        amount_usd: float,
        status: str = "OPEN",
        partial_exit_done: bool = False,
        entry_date: Optional[datetime] = None,
        exit_price: Optional[float] = None,
    ):
        self.id = id
        self.token_symbol = token_symbol
        self.token_address = token_address
        self.chain = chain
        self.entry_price = entry_price
        self.amount_usd = amount_usd
        self.status = status
        self.partial_exit_done = partial_exit_done
        self.entry_date = entry_date or datetime.now(timezone.utc)
        self.exit_price = exit_price
        # PnL porcentual calculado en tiempo real por ExitManager
        self.pnl_pct: float = 0.0

    @classmethod
    def from_db(cls, db_trade: DBTrade) -> "Trade":
        """Convierte un modelo ORM a un Trade DTO."""
        return cls(
            id=db_trade.id,
            token_symbol=db_trade.token_symbol,
            entry_price=float(db_trade.entry_price),
            amount_usd=float(db_trade.amount_usd),
            status=db_trade.status,
            entry_date=db_trade.created_at,
            exit_price=float(db_trade.exit_price) if db_trade.exit_price else None,
        )


# --------------------------------------------------------------------------- #
# Servicio principal
# --------------------------------------------------------------------------- #

class PortfolioService:
    """
    Servicio de gestión del portfolio.

    Todas las operaciones son asíncronas y transaccionales sobre SQLite.
    En entornos de test, los métodos `_inject_mock_trades` permiten inyectar
    datos sin tocar la DB.
    """

    def __init__(self) -> None:
        self._session_factory = async_session_factory
        logger.info("✓ PortfolioService inicializado (modo DB real)")

    # ------------------------------------------------------------------ #
    # Operaciones de lectura
    # ------------------------------------------------------------------ #

    async def get_open_trades(self) -> List[Trade]:
        """
        Recupera todos los trades con estado OPEN desde la base de datos.

        Returns:
            Lista de Trade DTOs con posiciones abiertas. Lista vacía si hay error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DBTrade).where(DBTrade.status == TradeStatus.OPEN.value)
                )
                db_trades = result.scalars().all()
                return [Trade.from_db(t) for t in db_trades]
        except Exception as exc:
            logger.error(f"[Portfolio] Error al obtener trades abiertos: {exc}")
            return []

    async def get_daily_pnl(self) -> float:
        """
        Calcula el PnL total acumulado de trades CERRADOS hoy (UTC).

        Fórmula por trade:
            base_amount = amount_usd / entry_price   (tokens comprados)
            pnl_trade   = (exit_price - entry_price) × base_amount

        Returns:
            PnL en USD (negativo = pérdida). 0.0 si no hay trades cerrados hoy.
        """
        try:
            async with self._session_factory() as session:
                today_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                result = await session.execute(
                    select(DBTrade).where(
                        and_(
                            DBTrade.status == TradeStatus.CLOSED.value,
                            DBTrade.updated_at >= today_start,
                        )
                    )
                )
                closed_trades = result.scalars().all()

                total_pnl = 0.0
                for t in closed_trades:
                    if t.exit_price and t.entry_price:
                        base_amount = float(t.amount_usd) / float(t.entry_price)
                        total_pnl += (float(t.exit_price) - float(t.entry_price)) * base_amount

                logger.debug(f"[Portfolio] PnL diario calculado: ${total_pnl:,.2f} ({len(closed_trades)} trades cerrados hoy)")
                return total_pnl

        except Exception as exc:
            logger.error(f"[Portfolio] Error al calcular PnL diario: {exc}")
            return 0.0

    async def get_portfolio_stats(self) -> dict:
        """
        Devuelve estadísticas resumidas del portfolio.

        Returns:
            dict con claves: total_invested, open_trades, closed_trades, daily_pnl.
        """
        try:
            open_trades = await self.get_open_trades()
            daily_pnl = await self.get_daily_pnl()
            total_invested = sum(t.amount_usd for t in open_trades)
            return {
                "total_invested": total_invested,
                "open_trades": len(open_trades),
                "daily_pnl": daily_pnl,
            }
        except Exception as exc:
            logger.error(f"[Portfolio] Error al obtener stats: {exc}")
            return {}

    async def check_persistence(self, symbol: str) -> bool:
        """
        Verifica si el token ha tenido actividad histórica en la DB.
        Útil para el SignalEngine al calcular el score de persistencia.

        Args:
            symbol: Ticker del token (ej. "ETH").

        Returns:
            True si el token aparece en el historial de trades, False si es nuevo.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DBTrade).where(DBTrade.token_symbol == symbol).limit(1)
                )
                exists = result.scalar_one_or_none() is not None
                logger.debug(f"[Portfolio] Persistencia de {symbol}: {'encontrado' if exists else 'nuevo token'}")
                return exists
        except Exception as exc:
            logger.error(f"[Portfolio] Error al verificar persistencia de {symbol}: {exc}")
            return False

    # ------------------------------------------------------------------ #
    # Operaciones de escritura
    # ------------------------------------------------------------------ #

    async def get_total_equity(self, current_prices: dict[str, float]) -> float:
        """
        Calcula Balance + PnL No Realizado. 
        Vital para el CircuitBreaker de Vicente.
        """
        open_trades = await self.get_open_trades()
        unrealized_pnl = 0.0
        
        for t in open_trades:
            cur_price = current_prices.get(t.token_symbol, t.entry_price)
            base_amount = t.amount_usd / t.entry_price
            unrealized_pnl += (cur_price - t.entry_price) * base_amount
            
        # Supongamos que el balance inicial es constante o viene de settings
        return settings.INITIAL_BALANCE + unrealized_pnl

    async def mark_partial_exit(self, trade_id: int) -> bool:
        """Persiste que se ha ejecutado el TP del 50%."""
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    result = await session.execute(
                        select(DBTrade).where(DBTrade.id == trade_id)
                    )
                    trade = result.scalar_one_or_none()
                    if trade:
                        trade.partial_exit_done = True
                        # Reducimos el amount_usd a la mitad para que el PnL siga cuadrando
                        trade.amount_usd = float(trade.amount_usd) * 0.5
                        return True
        except Exception as e:
            logger.error(f"[DB] Error marcando salida parcial: {e}")
            return False

    async def save_trade(
        self,
        token_symbol: str,
        token_address: str,
        chain: str,
        entry_price: float,
        amount_usd: float,
    ) -> bool:
        """
        Persiste un nuevo trade con estado OPEN en la base de datos.

        Args:
            token_symbol: Ticker del token (ej. "BTC").
            entry_price:  Precio de compra en USD.
            amount_usd:   Monto invertido en USD.

        Returns:
            True si se guardó correctamente, False en caso de error.
        """
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    new_trade = DBTrade(
                        token_symbol=token_symbol,
                        token_address=token_address,
                        chain=chain,
                        entry_price=entry_price,
                        amount_usd=amount_usd,
                        status=TradeStatus.OPEN.value,
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(new_trade)
            logger.info(f"[Portfolio] ✅ Trade guardado: {token_symbol} @ ${entry_price:.4f} (${amount_usd:.2f})")
            return True
        except Exception as exc:
            logger.error(f"[Portfolio] Error al guardar trade {token_symbol}: {exc}")
            return False

    async def close_trade(self, trade_id: int, exit_price: float) -> bool:
        """
        Actualiza un trade a estado CLOSED y registra el precio de salida.

        Args:
            trade_id:   ID del trade en la DB.
            exit_price: Precio de venta en USD.

        Returns:
            True si se actualizó correctamente, False si no se encontró o hubo error.
        """
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    result = await session.execute(
                        select(DBTrade).where(DBTrade.id == trade_id)
                    )
                    trade = result.scalar_one_or_none()

                    if not trade:
                        logger.warning(f"[Portfolio] Trade ID:{trade_id} no encontrado en DB.")
                        return False

                    trade.status = TradeStatus.CLOSED.value
                    trade.exit_price = exit_price
                    trade.updated_at = datetime.now(timezone.utc)

                    # Calcular PnL para el log
                    base_amount = float(trade.amount_usd) / float(trade.entry_price)
                    pnl = (exit_price - float(trade.entry_price)) * base_amount
                    logger.success(
                        f"[Portfolio] Trade ID:{trade_id} cerrado: "
                        f"{trade.token_symbol} | PnL: ${pnl:+.2f}"
                    )
            return True
        except Exception as exc:
            logger.error(f"[Portfolio] Error al cerrar trade ID:{trade_id}: {exc}")
            return False
