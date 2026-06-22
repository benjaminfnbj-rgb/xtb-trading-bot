import asyncio
import logging
import numpy as np
from datetime import datetime
from market_hours import is_market_open

logger = logging.getLogger(__name__)

SYMBOLS         = ["EURUSD", "XAUUSD"]
TIMEFRAME       = 5
EMA_FAST        = 5
EMA_SLOW        = 20
RSI_PERIOD      = 14
RSI_OVERSOLD    = 30
RSI_OVERBOUGHT  = 70
VOLUME          = 0.01
MAX_OPEN_TRADES = 2
LOOP_INTERVAL   = 60

SL_CONFIG = {"EURUSD": 0.0015, "XAUUSD": 1.50}
TP_CONFIG = {"EURUSD": 0.0030, "XAUUSD": 3.00}

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
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def get_signal(closes):
    if len(closes) < max(EMA_SLOW, RSI_PERIOD) + 5:
        return None
    ema_fast = compute_ema(closes, EMA_FAST)
    ema_slow = compute_ema(closes, EMA_SLOW)
    rsi      = compute_rsi(closes[-RSI_PERIOD * 2:], RSI_PERIOD)
    cross_up   = ema_fast[-2] < ema_slow[-2] and ema_fast[-1] > ema_slow[-1]
    cross_down = ema_fast[-2] > ema_slow[-2] and ema_fast[-1] < ema_slow[-1]
    if cross_up   and rsi < RSI_OVERBOUGHT: return "BUY"
    if cross_down and rsi > RSI_OVERSOLD:   return "SELL"
    return None

class TradingStrategy:
    def __init__(self, client, notifier):
        self.client   = client
        self.notifier = notifier

    async def run(self):
        logger.info("🚀 Stratégie démarrée — Exness MT5")
        await self.notifier.send(
            "🤖 *Bot Benjamin actif sur Exness !*\n"
            "📊 Instruments: EURUSD + XAUUSD\n"
            "⏱ Analyse toutes les 60 secondes\n"
            "🎯 Stratégie: EMA crossover + RSI\n"
            "🏦 Courtier: Exness MT5"
        )

        while True:
            try:
                await self._check_balance()
                for symbol in SYMBOLS:
                    await self._analyze(symbol)
                await asyncio.sleep(LOOP_INTERVAL)
            except Exception as e:
                logger.error(f"Erreur dans la boucle: {e}")
                raise  # remonte à main.py pour gestion retry

    async def _check_balance(self):
        result = await self.client.get_balance()
        balance = result.get("balance", 0)
        equity  = result.get("equity", 0)
        logger.info(f"💰 Balance: ${balance:.2f} | Equity: ${equity:.2f}")

    async def _analyze(self, symbol):
        if not is_market_open(symbol):
            logger.info(f"🔒 {symbol}: Marché fermé")
            return

        candles_resp = await self.client.get_candles(symbol, TIMEFRAME, count=100)
        candles = candles_resp.get("candles", [])
        if len(candles) < 50:
            logger.warning(f"Pas assez de données pour {symbol}")
            return

        closes = [c["close"] for c in candles]
        signal = get_signal(closes)

        if signal is None:
            logger.info(f"🔍 {symbol}: Pas de signal")
            return

        trades_resp = await self.client.get_open_trades()
        open_count  = len(trades_resp.get("positions", []))
        if open_count >= MAX_OPEN_TRADES:
            logger.info(f"⏸ Max trades atteint ({MAX_OPEN_TRADES})")
            return

        sym_info     = await self.client.get_symbol(symbol)
        current_price = sym_info.get("ask") if signal == "BUY" else sym_info.get("bid")
        sl_delta = SL_CONFIG.get(symbol, 0.0015)
        tp_delta = TP_CONFIG.get(symbol, 0.0030)

        if signal == "BUY":
            sl, tp, cmd = round(current_price - sl_delta, 5), round(current_price + tp_delta, 5), 0
        else:
            sl, tp, cmd = round(current_price + sl_delta, 5), round(current_price - tp_delta, 5), 1

        result = await self.client.open_trade(symbol, cmd, VOLUME, sl, tp)

        if result.get("result") == "ok":
            emoji = "🟢 BUY" if signal == "BUY" else "🔴 SELL"
            await self.notifier.send(
                f"{emoji} *{symbol}* sur Exness\n"
                f"📌 Prix: {current_price}\n"
                f"🛡 Stop Loss: {sl}\n"
                f"🎯 Take Profit: {tp}\n"
                f"📦 Lot: {VOLUME}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            logger.info(f"✅ Trade ouvert: {symbol} {signal} @ {current_price}")
        else:
            error = result.get("error", "Erreur inconnue")
            logger.error(f"❌ Trade échoué {symbol}: {error}")
