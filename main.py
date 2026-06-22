import asyncio
import logging
import os
import sys

from notifications import TelegramNotifier
from market_hours import is_market_open, MARKET_HOURS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ─── Variables d'environnement ───────────────────────────────────────────────
TG_TOKEN      = os.environ.get("TG_TOKEN")
TG_CHAT_ID    = os.environ.get("TG_CHAT_ID")

EXNESS_LOGIN  = os.environ.get("EXNESS_LOGIN")
EXNESS_PASS   = os.environ.get("EXNESS_PASSWORD")
EXNESS_SERVER = os.environ.get("EXNESS_SERVER", "Exness-MT5Real10")

def check_env():
    missing = []
    if not EXNESS_LOGIN:  missing.append("EXNESS_LOGIN")
    if not EXNESS_PASS:   missing.append("EXNESS_PASSWORD")
    if missing:
        logger.error(f"❌ Variables manquantes: {', '.join(missing)}")
        sys.exit(1)

def any_market_open():
    return any(is_market_open(s) for s in MARKET_HOURS)

async def wait_for_market_open(notifier, notified_ref):
    if not any_market_open():
        if not notified_ref[0]:
            logger.info("🔒 Marchés fermés — en attente silencieuse...")
            await notifier.send(
                "🔒 *Marchés fermés*\n"
                "Le bot attend la réouverture.\n"
                "📅 EURUSD + XAUUSD rouvrent dimanche soir."
            )
            notified_ref[0] = True
        await asyncio.sleep(300)
        return False
    else:
        notified_ref[0] = False
        return True

async def main():
    check_env()

    notifier = TelegramNotifier(TG_TOKEN, TG_CHAT_ID)

    # Import ici pour éviter crash si module absent
    from exness_client import ExnessClient
    from strategy import TradingStrategy

    client   = ExnessClient(EXNESS_LOGIN, EXNESS_PASS, EXNESS_SERVER)
    strategy = TradingStrategy(client, notifier)

    retry_count  = 0
    notified_ref = [False]  # évite spam Telegram marchés fermés

    while True:
        # ── Attente silencieuse si marchés fermés ───────────────────────
        if not await wait_for_market_open(notifier, notified_ref):
            continue

        try:
            logger.info("🔌 Connexion à Exness MT5...")
            await client.connect()
            retry_count = 0
            await strategy.run()

        except Exception as e:
            retry_count += 1
            wait_time = min(60 * retry_count, 600)  # max 10 min entre tentatives
            logger.error(f"❌ Erreur (tentative {retry_count}): {e}")

            # N'envoie une notif Telegram que toutes les 5 erreurs
            if retry_count % 5 == 1:
                await notifier.send(
                    f"⚠️ *Bot déconnecté*\n"
                    f"Erreur: {str(e)[:100]}\n"
                    f"Tentative {retry_count} — Reconnexion dans {wait_time}s..."
                )

            try:
                await client.disconnect()
            except:
                pass

            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
