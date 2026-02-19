import asyncio
from telegram import Bot
from app.core.config import settings
from loguru import logger

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send_alert(self, message: str) -> None:
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
            logger.info("Notificación enviada a Telegram.")
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")