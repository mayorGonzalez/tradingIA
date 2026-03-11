from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from app.models.db_models import Base
from app.core.config import settings  

'''
Este archivo es el "Bibliotecario" del proyecto.
Ahora es inteligente: lee la configuración de settings.py y se conecta 
automáticamente a Postgres en Docker o a SQLite en local.
'''
# URL dinámica desde el .env a través de Settings
DATABASE_URL = settings.DATABASE_URL

# FIX: engine lazy — se crea solo cuando se necesita, no al importar
_engine = None
_session_factory = None

def _make_engine():
    """
    FIX: Crea un engine con NullPool.
    NullPool no reutiliza conexiones entre requests, eliminando el conflicto
    de event loop entre el loop de Streamlit y el de asyncpg.
    Coste: una conexión nueva por operación — aceptable para este volumen.
    """
    return create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # <- clave: sin pool compartido entre loops
    )

def get_session_factory():
    """Devuelve un session factory con un engine fresco (NullPool)."""
    engine = _make_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

async def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas."""
    engine = _make_engine()
    async with engine.begin() as conn:
        # Esto creará las tablas en tradingia_db si no existen
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones para uso en dependencias."""
    factory = get_session_factory()
    async with factory() as session:
        yield session