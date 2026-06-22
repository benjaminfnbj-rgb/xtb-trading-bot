import asyncio
import json
import ssl
import websockets
import logging

logger = logging.getLogger(__name__)

# Serveurs Exness MT5
MT5_SERVERS = {
    "Exness-MT5Real10": "wss://mt5real10.exness.com:443/ws",
    "Exness-MT5Real":   "wss://mt5real.exness.com:443/ws",
    "Exness-MT5Trial":  "wss://mt5trial.exness.com:443/ws",
}

class ExnessClient:
    def __init__(self, login, password, server="Exness-MT5Real10"):
        self.login    = str(login)
        self.password = password
        self.server   = server
        self.ws       = None
        self.connected = False
        self._req_id  = 0

    def _next_id(self):
        self._req_id += 1
        return self._req_id

    async def connect(self):
        url = MT5_SERVERS.get(self.server)
        if not url:
            raise Exception(f"Serveur inconnu: {self.server}")

        ssl_ctx = ssl.create_default_context()
        self.ws = await websockets.connect(
            url,
            ssl=ssl_ctx,
            ping_interval=20,
            open_timeout=30
        )
        await self._login()
        self.connected = True

    async def _login(self):
        req = {
            "id":       self._next_id(),
            "command":  "login",
            "login":    self.login,
            "password": self.password
        }
        resp = await self._send(req)
        if resp.get("result") != "ok":
            raise Exception(f"Login Exness échoué: {resp}")
        logger.info("✅ Connecté à Exness MT5")

    async def _send(self, payload):
        await self.ws.send(json.dumps(payload))
        raw = await self.ws.recv()
        return json.loads(raw)

    async def get_balance(self):
        return await self._send({
            "id": self._next_id(),
            "command": "get_account_info"
        })

    async def get_symbol(self, symbol):
        return await self._send({
            "id": self._next_id(),
            "command": "get_symbol",
            "symbol": symbol
        })

    async def get_candles(self, symbol, period, count=100):
        import time
        return await self._send({
            "id": self._next_id(),
            "command": "get_candles",
            "symbol": symbol,
            "period": period,
            "count":  count,
            "from":   int(time.time()) - count * period * 60
        })

    async def open_trade(self, symbol, cmd_type, volume, sl=None, tp=None, comment="BotTrade"):
        sym = await self.get_symbol(symbol)
        price = sym.get("ask") if cmd_type == 0 else sym.get("bid")
        return await self._send({
            "id": self._next_id(),
            "command": "trade",
            "action":  "open",
            "symbol":  symbol,
            "type":    "buy" if cmd_type == 0 else "sell",
            "volume":  volume,
            "price":   price,
            "sl":      sl or 0,
            "tp":      tp or 0,
            "comment": comment
        })

    async def get_open_trades(self):
        return await self._send({
            "id": self._next_id(),
            "command": "get_positions"
        })

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
        self.connected = False
