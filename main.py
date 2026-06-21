import asyncio
import logging
import os
import sys

from xapi_client import XAPIClient
from strategy import TradingStrategy
from notifications import TelegramNotifier
from market_hours import is_market_open, MARKET_HOURS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

XTB_LOGIN    = os.environ.get("XTB_LOGIN")
XTB_PASSWORD = os.environ.get("XTB_PASSWORD")
XTB_TYPE     = os.environ.get("XTB_TYPE", "real")
TG_TOKEN     = os.environ.get("TG_TOKEN")
TG_CHAT_ID   = os.environ.get("TG_CHAT_ID")

def check_env():
    missing = []
    if not XTB_LOGIN:    missing.append("XTB_LOGIN")
    if not XTB_PASSWORD: missing.append("XTB_PASSWORD")
    if missing:
        logger.error(f"❌ Variables manquantes: {', '.join(missing)}")
        sys.exit(1)

def any_market_open():
    """Retourne True si au moins un marché est ouvert."""
    return any(is_market_open(s) for s in MARKET_HOURS)

async def wait_for_market_open(notifier):
    """Attend que les marchés rouvrent sans spammer Telegram."""
    notified = False
    while not any_market_open():
        if not notified:
            logger.info("🔒 Tous les marchés sont fermés — en attente...")
            await notifier.send(
                "🔒 *Marchés fermés*\n"
                "Le bot attend la réouverture.\n"
                "📅 EURUSD + XAUUSD rouvrent dimanche soir."
            )
            notified = True
        await asyncio.sleep(300)  # Vérifie toutes les 5 minutes, silencieusement

async def main():
    check_env()

    notifier = TelegramNotifier(TG_TOKEN, TG_CHAT_ID)
    client   = XAPIClient(XTB_LOGIN, XTB_PASSWORD, XTB_TYPE)
    strategy = TradingStrategy(client, notifier)

    retry_count = 0

    while True:
        # ── Attendre l'ouverture des marchés avant toute connexion XTB ──
        await wait_for_market_open(notifier)

        try:
            logger.info("🔌 Connexion à XTB...")
            await client.connect()
            retry_count = 0
            await strategy.run()

        except Exception as e:
            retry_count += 1
            wait_time = min(30 * retry_count, 300)
            logger.error(f"❌ Erreur critique (tentative {retry_count}): {e}")

            try:
                await notifier.send(
                    f"⚠️ *Bot déconnecté*\n"
                    f"Erreur: {str(e)[:100]}\n"
                    f"Reconnexion dans {wait_time}s..."
                )
            except:
                pass

            try:
                await client.disconnect()
            except:
                pass

            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
