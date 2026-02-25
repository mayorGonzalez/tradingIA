from loguru import logger
from app.core.config import settings
from app.infraestructure.exchange_client import ExchangeClient
from app.services.portfolio_service import PortfolioService
from app.services.notifier import TelegramNotifier

class ExitManager:
    def __init__(
        self, 
        portfolio_service: PortfolioService, 
        exchange_client: ExchangeClient,
        notifier: TelegramNotifier
    ) -> None:
        self.portfolio_service = portfolio_service
        self.exchange_client = exchange_client
        self.notifier = notifier

    async def check_open_positions(self) -> None:
        """
        Monitoriza trades abiertos y ejecuta salidas según TP/SL.
        """
        logger.info("Chequeando posiciones abiertas para posibles salidas...")
        open_trades = await self.portfolio_service.get_open_trades()

        if not open_trades:
            logger.info("No hay posiciones abiertas actualmente.")
            return

        for trade in open_trades:
            try:
                symbol = trade.token_symbol
                current_price = await self.exchange_client.fetch_ticker(symbol)

                if current_price is None:
                    continue

                # Calcular PnL porcentual
                pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                logger.debug(f"Checking {symbol}: {pnl_pct:+.2f}% (Price: ${current_price:,.4f})")

                # Reglas de Salida
                should_sell = False
                reason = ""

                if pnl_pct >= settings.TAKE_PROFIT_PCT:
                    should_sell = True
                    reason = f"TAKE PROFIT ({settings.TAKE_PROFIT_PCT}%)"
                elif pnl_pct <= settings.STOP_LOSS_PCT:
                    should_sell = True
                    reason = f"STOP LOSS ({settings.STOP_LOSS_PCT}%)"

                if should_sell:
                    logger.warning(f"SEÑAL DE SALIDA para {symbol}: {reason} | PnL: {pnl_pct:+.2f}%")
                    
                    # Calcular cantidad a vender (basado en el monto original y precio de entrada)
                    # En un sistema real, fetch_balance sería más seguro
                    amount_to_sell = trade.amount_usd / trade.entry_price
                    
                    # 1. Ejecutar venta en el Exchange
                    order = await self.exchange_client.create_market_sell_order(symbol, amount_to_sell)
                    
                    if order:
                        # 2. Actualizar DB
                        await self.portfolio_service.close_trade(trade.id, current_price)
                        
                        # 3. Notificar
                        report = (
                            f"🏁 <b>POSICIÓN CERRADA: {symbol}</b>\n"
                            f"📌 Razón: {reason}\n"
                            f"💰 PnL: <b>{pnl_pct:+.2f}%</b>\n"
                            f"💵 Precio Entrada: ${trade.entry_price:,.4f}\n"
                            f"📉 Precio Salida: ${current_price:,.4f}"
                        )
                        await self.notifier.send_alert(report)
                    else:
                        logger.error(f"Ocurrió un error al intentar vender {symbol}. Se reintentará en el próximo ciclo.")

            except Exception as e:
                logger.error(f"Error procesando salida para trade ID {trade.id}: {e}")
