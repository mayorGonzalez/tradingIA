import asyncio
import os
import psutil  # type: ignore
from loguru import logger

# Configuración de logs en archivo
logger.add("bot_final_check.log", rotation="10 MB", level="INFO")

from app.core.config import settings
from app.services.nansen_client import NansenClient
from app.services.nansen_mock import NansenMockClient
from app.services.nansen_validator import NansenSignalValidator
from app.services.signal_engine import SignalEngine
from app.services.notifier import TelegramNotifier
from app.services.risk_manager import RiskManager
from app.services.circuit_breaker import CircuitBreaker
from app.infraestructure.exchange_client import get_exchange_client, close_exchange_client
from app.infraestructure.database import init_db
from app.services.portfolio_service import PortfolioService
from app.services.exit_manager import ExitManager
from app.services.ai_analyst import AIAnalyst

# Variable global para control de apagado
shutdown_event = asyncio.Event()


async def health_check_task(portfolio: PortfolioService) -> None:
    """Tarea en segundo plano que imprime el estado del bot cada hora."""
    process = psutil.Process(os.getpid())
    while not shutdown_event.is_set():
        try:
            open_trades = await portfolio.get_open_trades()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            logger.info(
                f"📊 HEALTH CHECK | Bot activo | Trades abiertos: {len(open_trades)} | "
                f"Memoria usada: {memory_mb:.2f} MB"
            )
        except Exception as e:
            logger.error(f"Error en health check: {e}")

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            continue


async def trading_job() -> None:
    logger.info("--- Iniciando Ciclo de Trading Inteligente ---")

    # Inicialización de componentes (Exchange es Singleton)
    exchange = await get_exchange_client()
    portfolio = PortfolioService()
    notifier = TelegramNotifier()
    circuit_breaker = CircuitBreaker()

    # STEP 0: Seguridad de Emergencia (Primero de todo)
    prices = await exchange.get_all_tickers()
    total_equity = await portfolio.get_total_equity(prices)

    if await circuit_breaker.is_open(portfolio, total_equity):
        logger.warning("🛑 CIRCUIT BREAKER ABIERTO. Abortando ciclo.")
        return

    # STEP 1: Gestión de Salidas (Asegurar beneficios / cortar pérdidas)
    exit_manager = ExitManager(portfolio, exchange, notifier)

    try:
        await exit_manager.check_open_positions()
        logger.info("STEP 1 completado: Chequeo de salidas realizado.")

        # STEP 2: Obtener datos de Nansen en paralelo
        logger.info("STEP 2: Obteniendo datos de Nansen...")
        client = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
        raw_flows, holdings, dex_trades = await asyncio.gather(
            client.get_smart_money_flows(),
            client.get_smart_money_holdings(),
            client.get_dex_trades(),
            return_exceptions=True,
        )

        if isinstance(raw_flows, Exception):
            logger.error(f"[Main] Error crítico al obtener smart money flows: {raw_flows}")
            return  # Sin flows no podemos operar

        if isinstance(holdings, Exception):
            logger.warning(f"[Main] Holdings no disponibles: {holdings}")
            holdings = []

        if isinstance(dex_trades, Exception):
            logger.warning(f"[Main] DEX trades no disponibles: {dex_trades}")
            dex_trades = []

        # STEP 3: Validación y sanitización de señales
        logger.info("STEP 3: Validando y sanitizando flujos...")
        validator = NansenSignalValidator()
        clean_flows = validator.validate_flows(raw_flows)

        if not clean_flows:
            logger.info("No hay flujos válidos tras la sanitización. Abortando ciclo.")
            return

        logger.info(f"Flujos limpios: {len(clean_flows)}. Pasando al Engine...")

        # STEP 4: Motor de señales (Scoring)
        logger.info("STEP 4: Analizando flujos con SignalEngine...")
        engine = SignalEngine(exchange, portfolio)
        candidates = await engine.analyze_flows(
            flows=clean_flows,
            holdings=holdings,
            dex_trades=dex_trades,
        )

        # STEP 5: Filtro IA + Risk Management + Ejecución
        logger.info("STEP 5: Filtrando candidatos con IA y ejecutando...")
        ai_analyst = AIAnalyst()
        risk_manager = RiskManager(total_equity, await portfolio.get_current_exposure())

        for signal in [c for c in candidates if c.is_valid]:

            # Filtro IA: Gemini analiza contexto (pump artificial, calidad del SM, etc.)
            ai_verdict = await ai_analyst.analyze_opportunity(signal)
            if not ai_verdict.is_bullish:
                logger.info(f"🧠 Gemini rechazó {signal.token_symbol}: {ai_verdict.reason}")
                continue

            # Validación de riesgo financiero
            free_balance = await exchange.get_free_balance("USDT")
            if not risk_manager.validate_execution(signal, free_balance):
                continue

            position_size = risk_manager.calculate_position_size(signal.score)

            # Ejecución de la orden
            await notifier.send_alert(
                f"🚀 <b>COMPRANDO {signal.token_symbol}</b>\nIA: {ai_verdict.summary}"
            )
            order = await exchange.create_market_buy_order(signal.token_symbol, position_size)

            if order:
                # FIX: Registrar el trade en el RiskManager para actualizar
                # la exposición dentro del mismo ciclo y evitar sobreexposición
                risk_manager.register_trade(signal.token_symbol, position_size)

                # Persistencia con datos Multichain
                await portfolio.save_trade(
                    token_symbol=signal.token_symbol,
                    token_address=signal.token_address,
                    chain=signal.chain,
                    entry_price=order.get("price", signal.current_price),
                    amount_usd=position_size,
                )
                logger.success(f"✅ Posición abierta: {signal.token_symbol}")

    except Exception as e:
        logger.error(f"Error en trading_job: {e}", exc_info=True)


async def main() -> None:
    logger.info(f"TradingAI activo (DEBUG={settings.DEBUG_MODE})")

    # Inicializar base de datos
    await init_db()

    # Portfolio service para monitoreo
    portfolio = PortfolioService()

    # Iniciar monitor de salud en segundo plano
    health_task = asyncio.create_task(health_check_task(portfolio))

    try:
        while not shutdown_event.is_set():
            try:
                await trading_job()
            except Exception as e:
                logger.error(f"Error inesperado en trading_job: {e}", exc_info=True)

            logger.info(f"Ciclo terminado. Esperando {settings.POLLING_INTERVAL_MINUTES} min...")

            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=settings.POLLING_INTERVAL_MINUTES * 60,
                )
            except asyncio.TimeoutError:
                continue

    except asyncio.CancelledError:
        logger.warning("Apagado iniciado...")
    finally:
        shutdown_event.set()
        health_task.cancel()
        await close_exchange_client()
        logger.success("Bot detenido correctamente.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Bot detenido manualmente (Ctrl+C).")