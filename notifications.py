import aiohttp
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Notifications via Telegram Bot API.
    """

    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def send(self, message: str):
        if not self.token or not self.chat_id:
            logger.warning("Telegram non configuré — message ignoré")
            logger.info(f"[NOTIF] {message}")
            return

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info("✅ Notification Telegram envoyée")
                    else:
                        body = await resp.text()
                        logger.warning(f"⚠️ Telegram status: {resp.status} — {body}")
        except Exception as e:
            logger.error(f"Erreur notification Telegram: {e}")
