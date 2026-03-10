import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from app.core.config import settings
from loguru import logger

class TelegramNotifier:
    """
    Sistema de alertas en tiempo real.
    Usa HTML para evitar errores de parseo con símbolos de contratos.
    """
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        # Prioridad a los argumentos, fallback a settings
        self.token = token or settings.TELEGRAM_TOKEN.get_secret_value()
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token)
        
        # Semáforo para evitar baneo por spam en momentos de alta volatilidad
        self._message_semaphore = asyncio.Semaphore(5) 

    async def send_alert(self, message: str) -> None:
        """
        Envía alertas asíncronas.
        Usa ParseMode.HTML para mayor compatibilidad con direcciones de smart contracts.
        """
        if not self.token or not self.chat_id:
            logger.error("[Notifier] Faltan credenciales de Telegram. Alerta perdida.")
            return

        async with self._message_semaphore:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id, 
                    text=message, 
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True # Evita spam de links
                )
                logger.debug("[Notifier] Mensaje enviado correctamente.")
            except Exception as e:
                # Error crítico pero no bloqueante para el trading
                logger.error(f"[Notifier] Error al enviar a Telegram: {str(e)}")
                # No lanzamos excepción (raise) para que el bot siga operando