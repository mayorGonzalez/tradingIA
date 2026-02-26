import asyncio
import os
import psutil  # type: ignore
from typing import Union, List
from loguru import logger

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
    exchange = get_exchange_client()
    portfolio = PortfolioService()
    notifier = TelegramNotifier(token=settings.TELEGRAM_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)
    
    # Servicios de Análisis y Riesgo
    client: Union[NansenMockClient, NansenClient] = (
        NansenMockClient() if settings.DEBUG_MODE else NansenClient()
    )
    validator = NansenSignalValidator()
    engine = SignalEngine(exchange, portfolio, min_inflow_usd=settings.MIN_INFLOW_LIMIT)
    risk_manager = RiskManager(max_per_trade_usd=500.0)
    circuit_breaker = CircuitBreaker()
    exit_manager = ExitManager(portfolio, exchange, notifier)

    try:
        # STEP 1: Gestionar salidas de posiciones abiertas (TP/SL)
        await exit_manager.check_open_positions()

        # STEP 2: Obtener balance real para cálculos de riesgo
        balances = await exchange.get_balance()
        usdt_balance = balances.get('USDT', 0.0) if balances else 0.0
        
        if settings.DEBUG_MODE:
             usdt_balance = max(usdt_balance, 1000.0) # Simulación de balance para test

        # STEP 3: Circuit Breaker - ¿Es seguro operar hoy?
        if await circuit_breaker.is_open(portfolio, usdt_balance):
            logger.warning("🛑 Operaciones bloqueadas por Circuit Breaker (Límite de posiciones o Drawdown).")
            return

        # STEP 4: Obtener datos de Nansen (Paralelo)
        logger.info("Obteniendo datos de Nansen...")
        raw_flows, holdings, dex_trades = await asyncio.gather(
            client.get_smart_money_flows(),
            client.get_smart_money_holdings(),
            client.get_dex_trades(),
            return_exceptions=True
        )

        # Manejo de errores en la recolección distribuida
        if isinstance(raw_flows, Exception):
            logger.error(f"Error obteniendo flujos: {raw_flows}")
            return

        # STEP 5: Middleware de Validación y Sanitización
        clean_flows = validator.validate_flows(raw_flows)
        if not clean_flows:
            logger.info("No hay flujos válidos tras la sanitización.")
            return

        # STEP 6: Motor de Señales (Scoring)
        all_candidates = await engine.analyze_flows(
            flows=clean_flows,
            holdings=holdings if not isinstance(holdings, Exception) else [],
            dex_trades=dex_trades if not isinstance(dex_trades, Exception) else [],
        )
        
        # Filtrar solo las válidas por Score
        signals = [s for s in all_candidates if s.is_valid]

        # Inyección de Mock en modo DEBUG si no hay señales reales del mock
        if settings.DEBUG_MODE and not signals and all_candidates:
            logger.info("🛠️ DEBUG_MODE: Forzando señal de prueba para el primer candidato del mock.")
            signals = [all_candidates[0]]
            signals[0].is_valid = True

        if not signals:
            logger.info("Sin señales operables en este ciclo.")
            return

        for s in signals:
            # STEP 7: Risk Manager - Validación de Seguridad por Token
            if not risk_manager.validate_execution(s, usdt_balance):
                logger.warning(f"⚠️ {s.token_symbol} rechazado por RiskManager (Filtro de seguridad).")
                continue

            # STEP 8: Cálculo de Tamaño de Posición
            position_size = risk_manager.calculate_position_size(usdt_balance, s.score)
            
            # Ajuste para Testnet (mínimo $10)
            if settings.DEBUG_MODE:
                position_size = max(position_size, 11.0)
            
            if position_size >= 10.0:
                logger.success(f"🚀 EJECUTANDO COMPRA: {s.token_symbol} | Score: {s.score} | Monto: ${position_size}")
                
                # Alerta Pre-Ejecución
                await notifier.send_alert(f"🎯 <b>Señal Validada: {s.token_symbol}</b>\n⭐ Score: {s.score}/100\n⚖️ Inversión: ${position_size}")
                
                # Ejecución en Exchange
                order = await exchange.create_market_buy_order(s.token_symbol, position_size)
                
                if order:
                    # STEP 9: Persistencia y Gestión del Portfolio
                    entry_price = float(order.get('average', order.get('price', 0.0)))
                    if not entry_price:
                        ticker_price = await exchange.fetch_ticker(s.token_symbol)
                        entry_price = ticker_price if ticker_price else 0.0
                    
                    await portfolio.save_trade(
                        symbol=s.token_symbol,
                        price=entry_price,
                        amount=position_size
                    )
                    logger.success(f"✅ Compra completada y guardada: {s.token_symbol} @ {entry_price}")
                else:
                    logger.error(f"❌ Error crítico: La orden de {s.token_symbol} falló en el exchange.")
            else:
                logger.warning(f"Inversión calculada para {s.token_symbol} (${position_size}) es inferior al mínimo.")

    except Exception as e:
        logger.error(f"Error crítico en el ciclo de trading: {e}")

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