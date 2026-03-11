from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Float, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from typing import Optional

'''Este archivo define la "Arquitectura" de tu memoria a largo plazo.

Imagina que tu bot es un estudiante. Este archivo es el diseño de su cuaderno:
le dice exactamente dónde escribir la fecha de un trade, cuánto dinero invirtió,
cuánto ganó al salir, y si está abierto o cerrado.

Sin esto, el bot no sabría dónde apuntar sus ganancias o cómo recordar qué
operaciones están pendientes. Es la estructura de la base de datos.'''

class Base(DeclarativeBase):
    """Clase base para el mapeo declarativo."""
    pass

class TradeStatus(str, PyEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_symbol: Mapped[str] = mapped_column(String(20), index=True)

    # --- Auditoría de Estrategia ---
    is_paper_trade: Mapped[bool] = mapped_column(Boolean, default=True)
    entry_concentration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Datos Multichain (FIX: columnas que faltaban en el ORM) ---
    token_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    chain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    partial_exit_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Datos de Operación ---
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default=TradeStatus.OPEN.value)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Fechas ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Trade(symbol={self.token_symbol}, status={self.status}, entry={self.entry_price})>"