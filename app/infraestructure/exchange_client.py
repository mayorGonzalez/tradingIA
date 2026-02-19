import ccxt.async_support as ccxt
from app.core.config import settings
from loguru import logger

class ExchangeClient:
    def __init__(self) -> None:
        # Inicializamos Binance en modo sandbox (testnet) para seguridad
        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY.get_secret_value() if settings.BINANCE_API_KEY else None,
            'secret': settings.BINANCE_SECRET.get_secret_value() if settings.BINANCE_SECRET else None,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        # Activar modo prueba para no gastar dinero real durante el desarrollo
        self.exchange.set_sandbox_mode(True)

    async def get_balance(self) -> dict[str, float] | None:
        """Obtiene el balance disponible en la cuenta de prueba."""
        try:
            balance = await self.exchange.fetch_balance()
            # Filtramos solo lo que tiene saldo
            total_balance = {k: v for k, v in balance['total'].items() if v > 0}
            logger.info(f"Balance en Testnet: {total_balance}")
            return total_balance
        except Exception as e:
            logger.error(f"Error al conectar con el Exchange: {e}")
            return None

    async def close(self) -> None:
        # Muy importante cerrar la conexión asíncrona al terminar
        await self.exchange.close()