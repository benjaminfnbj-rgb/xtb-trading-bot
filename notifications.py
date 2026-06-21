import aiohttp
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class WhatsAppNotifier:
    """
    Utilise CallMeBot — API WhatsApp 100% gratuite.
    Activation requise UNE SEULE FOIS (voir README).
    """

    def __init__(self, phone_number, api_key=""):
        # Numéro au format international sans + (ex: 237692497780)
        self.phone = phone_number
        self.api_key = api_key
        self.base_url = "https://api.callmebot.com/whatsapp.php"

    async def send(self, message: str):
        if not self.phone or not self.api_key:
            logger.warning("WhatsApp non configuré — message ignoré")
            logger.info(f"[NOTIF] {message}")
            return

        encoded = urllib.parse.quote(message)
        url = f"{self.base_url}?phone={self.phone}&text={encoded}&apikey={self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info("✅ Notification WhatsApp envoyée")
                    else:
                        logger.warning(f"⚠️ WhatsApp status: {resp.status}")
        except Exception as e:
            logger.error(f"Erreur notification WhatsApp: {e}")
