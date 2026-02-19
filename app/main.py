import asyncio
from typing import Union
from loguru import logger

from app.core.config import settings
from app.models.nansen import NansenResponse
from app.services.nansen_client import NansenClient
from app.services.nansen_mock import NansenMockClient
from app.services.signal_engine import SignalEngine
from app.services.notifier import TelegramNotifier
from app.services.risk_manager import RiskManager
from app.infraestructure.exchange_client import ExchangeClient

async def trading_job() -> None:
    logger.info("--- Iniciando Ciclo de Trading Inteligente ---")
    
    # 1. Inicialización de componentes
    client: Union[NansenMockClient, NansenClient] = (
        NansenMockClient() if settings.DEBUG_MODE else NansenClient()
    )
    engine = SignalEngine(min_inflow_usd=settings.MIN_INFLOW_LIMIT)
    risk_manager = RiskManager(max_per_trade_usd=500.0) # Configurable
    exchange = ExchangeClient()
    notifier = TelegramNotifier(token=settings.TELEGRAM_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)

    try:
        # 2. Obtener datos y filtrar señales
        raw_data: NansenResponse = await client.get_smart_money_flows()
        signals = engine.analyze_flows(raw_data.data)

        if not signals:
            logger.info("No se detectaron señales operables en este ciclo.")
            return

        # 3. Consultar balance real (o testnet)
        # Para este ejemplo, simulamos que fetch_balance nos devuelve $1000 si falla la conexión
        balances = await exchange.get_balance()
        usdt_balance = balances.get('USDT', 1000.0) if balances else 1000.0

        for s in signals:
            # 4. Calcular tamaño de la posición
            position_size = risk_manager.calculate_position_size(usdt_balance)
            
            if position_size > 0:
                report = (
                    f"🎯 <b>Señal Detectada: {s.token_symbol}</b>\n"
                    f"💰 Inflow: ${s.net_flow_usd:,.2f}\n"
                    f"🏦 Balance actual: ${usdt_balance:,.2f}\n"
                    f"⚖️ Tamaño de orden calculado: <b>${position_size:,.2f}</b>"
                )
                logger.success(f"ORDEN CALCULADA: Comprar {s.token_symbol} con ${position_size}")
                await notifier.send_alert(report)
                
                # Aquí iría el comando de compra real: 
                # await exchange.create_order(s.token_symbol, position_size)
            else:
                logger.warning(f"Señal para {s.token_symbol} ignorada por falta de fondos o riesgo alto.")

    except Exception as e:
        logger.error(f"Error crítico en el ciclo de trading: {e}")
    finally:
        # Importante cerrar la conexión del exchange cada ciclo si no es persistente
        await exchange.close()

async def main() -> None:
    logger.info(f"TradingAI activo (DEBUG={settings.DEBUG_MODE})")
    await trading_job()

if __name__ == "__main__":
    asyncio.run(main())