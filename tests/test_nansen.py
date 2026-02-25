import asyncio
from app.services.nansen_client import NansenClient
from app.core.config import settings
from loguru import logger

async def test_nansen_connection():
    logger.info("🧪 Iniciando prueba de conexión con Nansen API...")
    logger.info(f"Endpoint: {settings.NANSEN_BASE_URL}")
    
    client = NansenClient()
    
    try:
        # Intentamos obtener flujos de las últimas 24h
        response = await client.get_smart_money_flows(chain="ethereum")
        
        logger.success("✅ Conexión exitosa con Nansen!")
        logger.info(f"Total de registros encontrados: {response.total_records}")
        
        if response.data:
            logger.info("Muestra de los primeros 3 tokens detectados:")
            for flow in response.data[:3]:
                logger.info(f"  - {flow.token_symbol} ({flow.token_address}): ${flow.net_flow_usd:,.2f}")
        else:
            logger.warning("La API respondió correctamente pero no hay datos de Smart Money en las últimas 24h.")
            
    except Exception as e:
        logger.error(f"❌ Error al conectar con Nansen: {e}")
        if "401" in str(e):
            logger.error("Error 401: Tu API Key parece ser inválida o ha expirado.")
        elif "429" in str(e):
            logger.error("Error 429: Has superado el límite de peticiones (Rate Limit).")

if __name__ == "__main__":
    logger.add("tests/test_output.log", rotation="500 MB")
    asyncio.run(test_nansen_connection())
