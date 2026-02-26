import ccxt.async_support as ccxt
from typing import Any, Dict, Optional
from app.core.config import settings
from loguru import logger
from app.core.utils import retry_async

_exchange_instance: Optional['ExchangeClient'] = None

class ExchangeClient:
    """
    Adaptador de Infraestructura para el Exchange (Binance/MEXC).
    
    Encapsula la complejidad de la librería CCXT y abstrae la comunicación
    con el mercado, garantizando que todas las operaciones se realicen
    en modo Sandbox durante el desarrollo.
    """

    def __init__(self) -> None:
        """
        Inicializa la conexión asíncrona con el exchange.
        Configura el modo Sandbox para prevenir ejecuciones en mercado real.
        """
        if settings.BINANCE_API_KEY and settings.BINANCE_API_KEY.get_secret_value():
            logger.info("Configurando Exchange: Binance (Testnet Mode)")
            self.exchange = ccxt.binance({
                'apiKey': settings.BINANCE_API_KEY.get_secret_value(),
                'secret': settings.BINANCE_SECRET.get_secret_value() if settings.BINANCE_SECRET else None,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'recvWindow': 60000  # 60 segundos de margen para desincronización de reloj
                }
            })
            self.exchange.set_sandbox_mode(True)
            self.name = "Binance"
        else:
            logger.info("Configurando Exchange: MEXC")
            self.exchange = ccxt.mexc({
                'apiKey': settings.MEXC_API_KEY.get_secret_value() if settings.MEXC_API_KEY else None,
                'secret': settings.MEXC_SECRET.get_secret_value() if settings.MEXC_SECRET else None,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'createMarketBuyOrderRequiresPrice': False,
                    'recvWindow': 60000
                }
            })
            self.name = "MEXC"
            try:
                self.exchange.set_sandbox_mode(True)
            except Exception:
                logger.warning("MEXC Sandbox no disponible o no soportado.")

    @retry_async()
    async def get_balance(self) -> dict[str, float] | None:
        """
        Recupera el inventario de activos disponibles.
        Filtra únicamente los activos con saldo positivo para optimizar el procesamiento.
        """
        try:
            balance = await self.exchange.fetch_balance()
            total_balance = {k: v for k, v in balance['total'].items() if v > 0}
            logger.info(f"Balance en {self.name}: {total_balance}")
            return total_balance
        except Exception as e:
            logger.error(f"Error al conectar con el Exchange: {e}")
            return None

    async def close(self) -> None:
        """Libera los recursos de red de la sesión asíncrona."""
        await self.exchange.close()

    @retry_async()
    async def fetch_ticker(self, symbol: str) -> float | None:
        """
        Obtiene el último precio de cierre (Last Price) para un par de trading.
        Normaliza el símbolo al formato estándar del exchange (BASE/QUOTE).
        """
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            ticker = await self.exchange.fetch_ticker(formatted_symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error al obtener precio de {symbol}: {e}")
            return None

    @retry_async()
    async def create_market_buy_order(self, symbol: str, amount_usd: float) -> dict[str, Any] | None:
        """
        Ejecuta una entrada forzada a mercado.
        Convierte una intención de inversión en USD en una orden de compra inmediata.
        """
        try:
            formatted_symbol = symbol if "/" in symbol else f"{symbol}/USDT"
            
            # En Binance Testnet y MEXC Spot usamos params para especificar la cantidad en USDT
            params = {}
            if self.name == "Binance":
                params["quoteOrderQty"] = amount_usd # Binance usa quoteOrderQty
            
            order = await self.exchange.create_order(
                symbol=formatted_symbol,
                type='market',
                side='buy',
                amount=amount_usd if self.name != "Binance" else None, 
                params=params
            )
            logger.success(f"ORDEN DE COMPRA {self.name} EJECUTADA: {formatted_symbol} | Inversión: ${amount_usd} USDT")
            return order 
        except Exception as e:
            logger.error(f"Error al ejecutar compra de {symbol}: {e}")
            return None

    @retry_async()
    async def create_market_sell_order(self, symbol: str, amount: float) -> dict[str, Any] | None:
        """
        Ejecuta una salida forzada a mercado.
        Liquida una posición existente de un activo base para retornar a la moneda estable (USDT).
        """
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            # En ventas, liquidamos la cantidad de tokens acumulados (base amount)
            order = await self.exchange.create_market_sell_order(formatted_symbol, amount)
            logger.success(f"ORDEN DE VENTA {self.name} EJECUTADA: {formatted_symbol} | Cantidad: {amount}")
            return order 
        except Exception as e:
            logger.error(f"Error al ejecutar venta de {symbol}: {e}")
            return None

    @retry_async()
    async def get_price_change_1h(self, symbol: str) -> float | None:
        """
        Calcula el momentum del precio en la última hora.
        Utiliza datos de velas OHLCV para determinar la volatilidad reciente
        y prevenir entradas en 'blow-off tops'.
        """
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            ohlcv = await self.exchange.fetch_ohlcv(formatted_symbol, timeframe='1h', limit=2)
            if len(ohlcv) < 2:
                return 0.0
            
            open_price = ohlcv[0][1] 
            close_price = ohlcv[1][4] 
            
            change = ((close_price - open_price) / open_price) * 100
            return change
        except Exception as e:
            logger.error(f"Error al obtener cambio 1h para {symbol}: {e}")
            return None

    @retry_async()
    async def get_24h_volume(self, symbol: str) -> float | None:
        """
        Mide la liquidez del activo en las últimas 24 horas.
        Vital para asegurar que el bot pueda entrar y salir de posiciones sin excesivo slippage.
        """
        try:
            formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
            ticker = await self.exchange.fetch_ticker(formatted_symbol)
            return float(ticker.get('quoteVolume', 0.0))
        except Exception as e:
            logger.error(f"Error al obtener volumen 24h para {symbol}: {e}")
            return None

def get_exchange_client() -> ExchangeClient:
    """Retorna la instancia única del cliente del exchange (Singleton)."""
    global _exchange_instance
    if _exchange_instance is None:
        _exchange_instance = ExchangeClient()
    return _exchange_instance

async def close_exchange_client() -> None:
    """Cierra la conexión global del exchange si existe."""
    global _exchange_instance
    if _exchange_instance:
        await _exchange_instance.close()
        _exchange_instance = None