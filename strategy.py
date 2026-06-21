import asyncio
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Paramètres stratégie ───────────────────────────────────────────────────
SYMBOLS = ["EURUSD", "XAUUSD"]       # Forex + Or
TIMEFRAME = 5                         # 5 minutes
EMA_FAST = 5
EMA_SLOW = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
VOLUME = 0.01                         # Lot minimum XTB
MAX_OPEN_TRADES = 2                   # Max trades simultanés
LOOP_INTERVAL = 60                    # Vérification toutes les 60 secondes

# SL/TP en valeur prix réelle (pas en pips universels)
# EURUSD : 1 pip = 0.0001  → SL 15 pips = 0.0015 / TP 30 pips = 0.0030
# XAUUSD : 1 point = 0.10$ → SL 1.50$ = 0.150  / TP 3.00$ = 3.00
SL_CONFIG = {
    "EURUSD": 0.0015,   # 15 pips Forex
    "XAUUSD": 1.50,     # 1.50$ sur l'or
}
TP_CONFIG = {
    "EURUSD": 0.0030,   # 30 pips Forex (ratio 1:2)
    "XAUUSD": 3.00,     # 3.00$ sur l'or (ratio 1:2)
}
# ────────────────────────────────────────────────────────────────────────────

def compute_ema(prices, period):
    prices = np.array(prices, dtype=float)
    k = 2 / (period + 1)
    ema = [prices[0]]
    for p in prices[1:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema

def compute_rsi(prices, period=14):
    prices = np.array(prices, dtype=float)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_signal(closes):
    if len(closes) < max(EMA_SLOW, RSI_PERIOD) + 5:
        return None

    ema_fast = compute_ema(closes, EMA_FAST)
    ema_slow = compute_ema(closes, EMA_SLOW)
    rsi = compute_rsi(closes[-RSI_PERIOD * 2:], RSI_PERIOD)

    cross_up = ema_fast[-2] < ema_slow[-2] and ema_fast[-1] > ema_slow[-1]
    cross_down = ema_fast[-2] > ema_slow[-2] and ema_fast[-1] < ema_slow[-1]

    if cross_up and rsi < RSI_OVERBOUGHT:
        return "BUY"
    if cross_down and rsi > RSI_OVERSOLD:
        return "SELL"
    return None

class TradingStrategy:
    def __init__(self, client, notifier):
        self.client = client
        self.notifier = notifier
        self.open_trades = {}

    async def run(self):
        logger.info("🚀 Stratégie démarrée — Forex + Or 24h/24")
        await self.notifier.send(
            "🤖 *Bot Benjamin actif !*\n"
            "📊 Instruments: EURUSD + XAUUSD\n"
            "⏱ Analyse toutes les 60 secondes\n"
            "🎯 Stratégie: EMA crossover + RSI"
        )

        while True:
            try:
                await self._check_balance()
                for symbol in SYMBOLS:
                    await self._analyze(symbol)
                await asyncio.sleep(LOOP_INTERVAL)
            except Exception as e:
                logger.error(f"Erreur stratégie: {e}")
                await self.notifier.send(f"⚠️ Erreur bot: {str(e)}")
                await asyncio.sleep(30)

    async def _check_balance(self):
        result = await self.client.get_balance()
        if result.get("status") is True:
            data = result["returnData"]
            balance = data.get("balance", 0)
            equity = data.get("equity", 0)
            logger.info(f"💰 Balance: ${balance:.2f} | Equity: ${equity:.2f}")

    async def _analyze(self, symbol):
        # Récupérer les bougies
        candles_resp = await self.client.get_candles(symbol, TIMEFRAME, count=100)
        if candles_resp.get("status") is not True:
            logger.warning(f"Impossible de récupérer les bougies pour {symbol}")
            return

        rate_infos = candles_resp["returnData"].get("rateInfos", [])
        if len(rate_infos) < 50:
            logger.warning(f"Pas assez de données pour {symbol}")
            return

        closes = [c["open"] + c["close"] for c in rate_infos]
        signal = get_signal(closes)

        if signal is None:
            logger.info(f"🔍 {symbol}: Pas de signal clair")
            return

        # Vérifier si on a déjà trop de trades ouverts
        trades_resp = await self.client.get_open_trades()
        open_count = len(trades_resp.get("returnData", []))
        if open_count >= MAX_OPEN_TRADES:
            logger.info(f"⏸ Max trades atteint ({MAX_OPEN_TRADES}), on attend")
            return

        # Calculer SL et TP (valeurs fixes par instrument, pas en "pips universels")
        symbol_info = await self.client.get_symbol(symbol)
        current_price = symbol_info["returnData"]["ask"] if signal == "BUY" else symbol_info["returnData"]["bid"]
        sl_delta = SL_CONFIG.get(symbol, 0.0015)
        tp_delta = TP_CONFIG.get(symbol, 0.0030)

        if signal == "BUY":
            sl = round(current_price - sl_delta, 5)
            tp = round(current_price + tp_delta, 5)
            cmd_type = 0
        else:
            sl = round(current_price + sl_delta, 5)
            tp = round(current_price - tp_delta, 5)
            cmd_type = 1

        # Ouvrir le trade
        result = await self.client.open_trade(symbol, cmd_type, VOLUME, sl, tp)

        if result.get("status") is True:
            order_id = result["returnData"]["order"]
            emoji = "🟢 BUY" if signal == "BUY" else "🔴 SELL"
            msg = (
                f"{emoji} *{symbol}*\n"
                f"📌 Prix: {current_price}\n"
                f"🛡 Stop Loss: {sl}\n"
                f"🎯 Take Profit: {tp}\n"
                f"📦 Lot: {VOLUME}\n"
                f"🆔 Order: {order_id}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            await self.notifier.send(msg)
            logger.info(f"✅ Trade ouvert: {symbol} {signal} @ {current_price}")
        else:
            error = result.get("errorDescr", "Erreur inconnue")
            logger.error(f"❌ Trade échoué {symbol}: {error}")
            await self.notifier.send(f"❌ Trade échoué sur {symbol}: {error}")
