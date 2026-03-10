import asyncio
import os
import psutil  # type: ignore
from typing import Union, List
from loguru import logger

# Configuración de logs en archivo
logger.add("bot_final_check.log", rotation="10 MB", level="INFO")

from app.core.config import settings
from app.models.nansen import NansenResponse, SignalResult
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
    
    # 1. Inicialización de componentes (Exchange es Singleton)
    exchange = await get_exchange_client()
    portfolio = PortfolioService()
    notifier = TelegramNotifier()
    circuit_breaker = CircuitBreaker()
    
    # STEP 0: Seguridad de Emergencia (Primero de todo)
    # Obtenemos Equity total para el breaker
    prices = await exchange.get_all_tickers() # Necesario para PnL flotante
    total_equity = await portfolio.get_total_equity(prices)
    
    if await circuit_breaker.is_open(portfolio, total_equity):
        logger.warning("🛑 CIRCUIT BREAKER ABIERTO. Abortando ciclo.")
        return

    # STEP 1: Gestión de Salidas (Asegurar beneficios/cortar pérdidas)
    exit_manager = ExitManager(portfolio, exchange, notifier)
        
    try:
        # STEP 1: Gestionar salidas de posiciones abiertas (TP/SL)
        await exit_manager.check_open_positions()
        logger.info("STEP 1 Completado: Chequeo de salidas realizado.")

        # STEP 4: Obtener datos de Nansen (Paralelo)
        logger.info("Obteniendo datos de Nansen...")
        client = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
        raw_flows, holdings, dex_trades = await asyncio.gather(
            client.get_smart_money_flows(),
            client.get_smart_money_holdings(),
            client.get_dex_trades(),
            return_exceptions=True
        )

        # Manejo de errores en la recolección distribuida
        if isinstance(raw_flows, Exception):
            logger.error(f"[Main] Error crítico al obtener smart money flows: {raw_flows}")
            return  # Sin flows no podemos operar
        if isinstance(holdings, Exception):
            logger.warning(f"[Main] Holdings no disponibles: {holdings}")
            holdings = []
        if isinstance(dex_trades, Exception):
            logger.warning(f"[Main] DEX trades no disponibles: {dex_trades}")
            dex_trades = []


        validator = NansenSignalValidator()
        engine = SignalEngine(exchange, portfolio)
        ai_analyst = AIAnalyst() # Gemini 1.5 Pro integrado
        # STEP 5: Middleware de Validación y Sanitización
        clean_flows = validator.validate_flows(raw_flows)
        if not clean_flows:
            logger.info("No hay flujos válidos tras la sanitización del validador.")
            return
        
        logger.info(f"Flujos limpios: {len(clean_flows)}. Pasando al Engine...")

        # STEP 6: Motor de Señales (Scoring)
        candidates = await engine.analyze_flows(
            flows=clean_flows,
            holdings=holdings if not isinstance(holdings, Exception) else [],
            dex_trades=dex_trades if not isinstance(dex_trades, Exception) else [],
        )
        
        # Filtramos por Score y luego por IA
        for s in [c for c in candidates if c.is_valid]: 
            # --- EL FILTRO DE VICENTE ---
            # Gemini analiza el contexto (¿Quién es el SM? ¿Hay pump artificial?)
            ai_verdict = await ai_analyst.analyze_opportunity(s)
            if not ai_verdict.is_bullish:
                logger.info(f"🧠 Gemini rechazó {s.token_symbol}: {ai_verdict.reason}")
                continue

            # STEP 4: Risk Management & Execution
            risk_manager = RiskManager(total_equity, await portfolio.get_current_exposure())
            if not risk_manager.validate_execution(s, await exchange.get_free_balance("USDT")):
                continue

            position_size = risk_manager.calculate_position_size(s.score)
            
            # EJECUCIÓN
            await notifier.send_alert(f"🚀 <b>COMPRANDO {s.token_symbol}</b>\nIA: {ai_verdict.summary}")
            order = await exchange.create_market_buy_order(s.token_symbol, position_size)
            
            if order:
                # Persistencia con datos Multichain
                await portfolio.save_trade(
                    token_symbol=s.token_symbol,
                    token_address=s.token_address,
                    chain=s.chain,
                    entry_price=order.get('price', s.current_price),
                    amount_usd=position_size
                )
                logger.success(f"✅ Posición abierta: {s.token_symbol}")

    except Exception as e:
        logger.error(f"Error in trading_job: {e}")

async def main() -> None:
    logger.info(f"TradingAI activo (DEBUG={settings.DEBUG_MODE})")

    # Inicializar base de datos
    await init_db()

    # Portfolio service para monitoreo
    portfolio = PortfolioService()

    # Iniciar monitor de salud
    health_task = asyncio.create_task(health_check_task(portfolio))

    try:
        while not shutdown_event.is_set():
            try:
                await trading_job()
            except Exception as e:
                logger.error(f"Error inesperado en trading_job: {e}")

            logger.info(f"Ciclo terminado. Esperando {settings.POLLING_INTERVAL_MINUTES} min...")

            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=settings.POLLING_INTERVAL_MINUTES * 60
                )
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        logger.warning("Apagado iniciado...")
    finally:
        shutdown_event.set()
        health_task.cancel()
        # Cleanup del Exchange Singleton
        await close_exchange_client()
        logger.success("Bot detenido correctamente.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Bot detenido manualmente (Ctrl+C).")