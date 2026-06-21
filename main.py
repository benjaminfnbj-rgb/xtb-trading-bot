import asyncio
import logging
import os
import sys

from xapi_client import XAPIClient
from strategy import TradingStrategy
from notifications import WhatsAppNotifier

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ─── Variables d'environnement ───────────────────────────────────────────────
XTB_LOGIN    = os.environ.get("XTB_LOGIN")
XTB_PASSWORD = os.environ.get("XTB_PASSWORD")
XTB_TYPE     = os.environ.get("XTB_TYPE", "real")       # "real" ou "demo"
WA_PHONE     = os.environ.get("WA_PHONE")               # ex: 237692497780
WA_APIKEY    = os.environ.get("WA_APIKEY")              # clé CallMeBot

def check_env():
    missing = []
    if not XTB_LOGIN:    missing.append("XTB_LOGIN")
    if not XTB_PASSWORD: missing.append("XTB_PASSWORD")
    if missing:
        logger.error(f"❌ Variables manquantes: {', '.join(missing)}")
        sys.exit(1)

async def main():
    check_env()

    notifier = WhatsAppNotifier(WA_PHONE, WA_APIKEY)
    client   = XAPIClient(XTB_LOGIN, XTB_PASSWORD, XTB_TYPE)
    strategy = TradingStrategy(client, notifier)

    retry_count = 0

    while True:
        try:
            logger.info("🔌 Connexion à XTB...")
            await client.connect()
            retry_count = 0
            await strategy.run()

        except Exception as e:
            retry_count += 1
            wait_time = min(30 * retry_count, 300)  # Max 5 minutes
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
