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

# Motor asíncrono configurado por el usuario
engine = create_async_engine(DATABASE_URL, echo=False)

async def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas."""
    async with engine.begin() as conn:
        # Esto creará las tablas en tradingia_db si no existen
        await conn.run_sync(Base.metadata.create_all)

# Creador de sesiones asíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones para uso en dependencias."""
    async with async_session_factory() as session:
        yield session