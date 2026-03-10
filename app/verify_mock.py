import os
import sys
import asyncio
from loguru import logger

# Asegurar que el directorio raíz está en el PYTHONPATH
sys.path.append(os.getcwd())

from app.core.config import settings
from app.main import main

async def run_verification():
    """
    Script de conveniencia para ejecutar el bot con NansenMockClient.
    Forzamos DEBUG_MODE=True y POLLING_INTERVAL=1 para testing rápido.
    """
    print("\n" + "="*50)
    print("🚀 INICIANDO VERIFICACIÓN DE NANSEN MOCK")
    print("="*50)
    print(f"Modo: {'DEBUG (🛠️ MOCK)' if settings.DEBUG_MODE else 'PRODUCCIÓN (⚠️ API REAL)'}")
    print(f"Polling: {settings.POLLING_INTERVAL_MINUTES} minuto(s)")
    print("="*50 + "\n")

    if not settings.DEBUG_MODE:
        logger.warning("Instrucción: DEBUG_MODE=False detectado. Cambiando a True para este test...")
        settings.DEBUG_MODE = True

    try:
        # Ejecutar el main original del bot
        await main()
    except KeyboardInterrupt:
        print("\n👋 Verificación detenida por el usuario.")
    except Exception as e:
        logger.error(f"Error durante la verificación: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_verification())
    except KeyboardInterrupt:
        pass
