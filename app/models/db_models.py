from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Float, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from typing import Optional

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
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default=TradeStatus.OPEN.value)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Trade(symbol={self.token_symbol}, status={self.status}, entry={self.entry_price})>"
