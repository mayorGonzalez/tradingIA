import asyncio
import os
import psutil  # type: ignore
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
from app.infraestructure.database import init_db
from app.services.portfolio_service import PortfolioService
from app.services.exit_manager import ExitManager

# Variable global para control de apagado
shutdown_event = asyncio.Event()

async def health_check_task(portfolio: PortfolioService) -> None:
    """Tarea en segundo plano que imprime el estado del bot cada hora."""
    process = psutil.Process(os.getpid())
    while not shutdown_event.is_set():
        try:
            # Stats básicas
            open_trades = await portfolio.get_open_trades()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            logger.info(
                f"📊 HEALTH CHECK | Bot activo | Trades abiertos: {len(open_trades)} | "
                f"Memoria usada: {memory_mb:.2f} MB"
            )
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            
        # Esperar 1 hora (o hasta que se apague)
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            continue


async def trading_job() -> None:
    logger.info("--- Iniciando Ciclo de Trading Inteligente ---")
    
    # 1. Inicialización de componentes
    client: Union[NansenMockClient, NansenClient] = (
        NansenMockClient() if settings.DEBUG_MODE else NansenClient()
    )
    exchange = ExchangeClient()
    portfolio = PortfolioService()
    engine = SignalEngine(exchange, portfolio, min_inflow_usd=settings.MIN_INFLOW_LIMIT)
    risk_manager = RiskManager(max_per_trade_usd=500.0) # Configurable
    notifier = TelegramNotifier(token=settings.TELEGRAM_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)
    exit_manager = ExitManager(portfolio, exchange, notifier)

    try:
        # 1.5 Gestionar salidas de posiciones abiertas
        await exit_manager.check_open_positions()

        # 2. Obtener datos de Nansen en paralelo (3 fuentes)
        logger.info("Obteniendo datos de Nansen (netflow + holdings + DEX trades)...")
        raw_data, holdings, dex_trades = await asyncio.gather(
            client.get_smart_money_flows(),
            client.get_smart_money_holdings(),
            client.get_dex_trades(),
        )

        # 3. Scoring multidimensional
        all_candidates = await engine.analyze_flows(
            flows=raw_data.data,
            holdings=holdings,
            dex_trades=dex_trades,
        )
        
        # Filtrar solo las válidas (Score > MIN_SCORE_THRESHOLD)
        signals = [s for s in all_candidates if s.is_valid]

        if not signals:
            logger.info("No se detectaron señales operables con puntuación suficiente en este ciclo.")
            return

        # 3. Consultar balance real (o testnet)
        balances = await exchange.get_balance()
        usdt_balance = balances.get('USDT', 1000.0) if balances else 1000.0

        for s in signals:
            # 4. Calcular tamaño de la posición
            position_size = risk_manager.calculate_position_size(usdt_balance)
            
            if position_size > 0:
                report = (
                    f"🎯 <b>Señal Detectada: {s.token_symbol}</b>\n"
                    f"⭐ Score: <b>{s.score}/100</b>\n"
                    f"💰 Inflow: ${s.net_flow_usd:,.2f}\n"
                    f"🏦 Balance actual: ${usdt_balance:,.2f}\n"
                    f"⚖️ Tamaño de orden calculado: <b>${position_size:,.2f}</b>"
                )
                logger.success(f"ORDEN CALCULADA: Comprar {s.token_symbol} (Score: {s.score}) con ${position_size}")
                await notifier.send_alert(report)
                
                # Ejecución de compra real
                order = await exchange.create_market_buy_order(s.token_symbol, position_size)
                
                if order:
                    # Guardar en base de datos para seguimiento
                    entry_price = float(order.get('price', 0.0)) or await exchange.fetch_ticker(s.token_symbol) or 0.0
                    await portfolio.save_trade(
                        symbol=s.token_symbol,
                        price=entry_price,
                        amount=position_size
                    )
            else:
                logger.warning(f"Señal para {s.token_symbol} ignorada por falta de fondos o riesgo alto.")

    except Exception as e:
        logger.error(f"Error crítico en el ciclo de trading: {e}")
    finally:
        # Importante cerrar la conexión del exchange cada ciclo si no es persistente
        await exchange.close()

async def main() -> None:
    logger.info(f"TradingAI activo (DEBUG={settings.DEBUG_MODE})")

    # Inicializar base de datos
    await init_db()

    # Portfolio service para el health check
    portfolio = PortfolioService()

    # Iniciar monitor de salud en segundo plano
    health_task = asyncio.create_task(health_check_task(portfolio))

    try:
        while not shutdown_event.is_set():
            try:
                await trading_job()
            except Exception as e:
                logger.error(f"Error inesperado en el loop principal: {e}")

            logger.info(f"Esperando {settings.POLLING_INTERVAL_MINUTES} minutos para el siguiente ciclo...")

            # Esperar el intervalo o hasta que se pida apagado (Ctrl+C)
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=settings.POLLING_INTERVAL_MINUTES * 60
                )
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        # Lanzado cuando el task es cancelado externamente (p.ej. Ctrl+C en Windows)
        logger.warning("Tarea cancelada. Iniciando apagado seguro...")
    finally:
        # Cleanup final — siempre se ejecuta, incluso con Ctrl+C
        logger.warning("Realizando limpieza final de recursos...")
        shutdown_event.set()   # Notificar a todas las tareas que deben parar
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        logger.success("Bot detenido correctamente. ¿Hasta pronto!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Windows lanza KeyboardInterrupt directamente en lugar de SIGINT
        logger.warning("Ctrl+C detectado. El bot se ha detenido.")