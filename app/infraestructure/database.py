from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from app.models.db_models import Base

# URL de la base de datos SQLite asíncrona
DATABASE_URL = "sqlite+aiosqlite:///./trading_v2.db"

# Motor asíncrono
engine = create_async_engine(DATABASE_URL, echo=False)

async def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Creador de sesiones asíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones para uso en dependencias o contextos asíncronos."""
    async with async_session_factory() as session:
        yield session
