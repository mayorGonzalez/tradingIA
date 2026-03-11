from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from app.models.db_models import Base
from app.core.config import settings  # <--- IMPORTANTE: Usamos tus settings

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

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    return _engine

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory

# Compatibilidad hacia atrás — los servicios usan async_session_factory directamente
@property
def async_session_factory():
    return get_session_factory()

async def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas."""
    async with get_engine().begin() as conn:
        # Esto creará las tablas en tradingia_db si no existen
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones para uso en dependencias."""
    async with async_session_factory() as session:
        yield session