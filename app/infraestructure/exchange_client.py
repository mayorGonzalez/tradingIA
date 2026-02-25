import ccxt.async_support as ccxt
from typing import Any
from app.core.config import settings
from loguru import logger
from app.core.utils import retry_async

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

    @retry_async()
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

    @retry_async()
    async def fetch_ticker(self, symbol: str) -> float | None:
        """Obtiene el precio actual de un token (ej: ETH -> ETH/USDT)."""
        try:
            # Aseguramos formato ccxt (Base/Quote)
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            ticker = await self.exchange.fetch_ticker(formatted_symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error al obtener precio de {symbol}: {e}")
            return None

    @retry_async()
    async def create_market_buy_order(self, symbol: str, amount_usd: float) -> dict[str, Any] | None:
        """Ejecuta una orden de compra a mercado."""
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            # En Binance, market buy puede ser por cantidad de base o quote
            # Usamos params para especificar que el amount es en USDT (quote)
            order = await self.exchange.create_market_buy_order(formatted_symbol, amount_usd)
            logger.success(f"ORDEN DE COMPRA EJECUTADA: {formatted_symbol} | Amount: ${amount_usd}")
            return order  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error al ejecutar compra de {symbol}: {e}")
            return None

    @retry_async()
    async def create_market_sell_order(self, symbol: str, amount: float) -> dict[str, Any] | None:
        """Ejecuta una orden de venta a mercado."""
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            # En testnet/sandbox, create_order funcionará igual
            order = await self.exchange.create_market_sell_order(formatted_symbol, amount)
            logger.success(f"ORDEN DE VENTA EJECUTADA: {formatted_symbol} | Cantidad: {amount}")
            return order  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error al ejecutar venta de {symbol}: {e}")
            return None

    @retry_async()
    async def get_price_change_1h(self, symbol: str) -> float | None:
        """Calcula el cambio porcentual de precio en la última hora."""
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            # Obtenemos las últimas 2 velas de 1 hora
            ohlcv = await self.exchange.fetch_ohlcv(formatted_symbol, timeframe='1h', limit=2)
            if len(ohlcv) < 2:
                return 0.0
            
            open_price = ohlcv[0][1] # Open de la vela anterior
            close_price = ohlcv[1][4] # Close de la vela actual (o precio actual)
            
            change = ((close_price - open_price) / open_price) * 100
            return change
        except Exception as e:
            logger.error(f"Error al obtener cambio 1h para {symbol}: {e}")
            return None

    @retry_async()
    async def get_24h_volume(self, symbol: str) -> float | None:
        """Obtiene el volumen de trading de las últimas 24h en USDT."""
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            ticker = await self.exchange.fetch_ticker(formatted_symbol)
            return float(ticker.get('quoteVolume', 0.0))
        except Exception as e:
            logger.error(f"Error al obtener volumen 24h para {symbol}: {e}")
            return None