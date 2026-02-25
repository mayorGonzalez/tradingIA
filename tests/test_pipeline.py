"""
Test completo del pipeline de señales con datos REALES de Nansen.
Llama a los 3 endpoints, cruza la información y muestra el ranking final.
"""
import asyncio
from loguru import logger
from app.services.nansen_client import NansenClient
from app.services.signal_engine import SignalEngine
from app.core.config import settings
from app.infraestructure.database import init_db
from app.infraestructure.exchange_client import ExchangeClient
from app.services.portfolio_service import PortfolioService


async def test_full_pipeline():
    logger.add("tests/test_output.log", rotation="500 MB")
    logger.info("=" * 60)
    logger.info("🚀 TEST COMPLETO DEL PIPELINE DE SEÑALES (API REAL)")
    logger.info(f"Umbral mínimo de inflow: ${settings.MIN_INFLOW_LIMIT:,.0f}")
    logger.info(f"Score mínimo para señal válida: {settings.MIN_SCORE_THRESHOLD}")
    logger.info("=" * 60)

    await init_db()

    nansen = NansenClient()
    exchange = ExchangeClient()
    portfolio = PortfolioService()
    engine = SignalEngine(exchange, portfolio, min_inflow_usd=settings.MIN_INFLOW_LIMIT)

    try:
        logger.info("📡 Consultando 3 endpoints de Nansen en paralelo...")
        flows, holdings, dex_trades = await asyncio.gather(
            nansen.get_smart_money_flows(chain="ethereum"),
            nansen.get_smart_money_holdings(chain="ethereum"),
            nansen.get_dex_trades(chain="ethereum"),
        )

        logger.info(f"  → Netflow:   {len(flows.data)} tokens")
        logger.info(f"  → Holdings:  {len(holdings)} tokens en cartera")
        logger.info(f"  → DEX Trades: {len(dex_trades)} operaciones recientes")

        logger.info("")
        logger.info("🔬 Ejecutando scoring multidimensional...")
        results = await engine.analyze_flows(
            flows=flows.data,
            holdings=holdings,
            dex_trades=dex_trades,
        )

        logger.info("")
        logger.info("📊 RANKING DE SEÑALES:")
        logger.info("-" * 60)
        for r in results:
            emoji = "✅" if r.is_valid else "⚠️ "
            logger.info(
                f"{emoji} {r.token_symbol:<15} "
                f"Score={r.score:>6.1f}  "
                f"Inflow=${r.net_flow_usd:>10,.0f}  "
                f"Holders={r.holders_count}  "
                f"DEX_buys={r.dex_buy_count}  "
                f"7d={'✓' if r.trend_confirmed_7d else '✗'}  "
                f"Risks={r.risk_factors if r.risk_factors else '-'}"
            )

        valid = [r for r in results if r.is_valid]
        logger.info("-" * 60)
        logger.info(f"✅ {len(valid)} señales válidas listas para operar")

    except Exception as e:
        logger.error(f"Error en el test: {e}")
    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
