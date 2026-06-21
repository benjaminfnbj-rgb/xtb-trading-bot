import asyncio
import json
import ssl
import websockets
import logging

logger = logging.getLogger(__name__)

SERVERS = {
    "real": "wss://xapi.xtb.com:5112/websocket",
    "demo": "wss://xapi.xtb.com:5124/websocket"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://xstation5.xtb.com",
}

class XAPIClient:
    def __init__(self, login, password, account_type="real"):
        self.login = login
        self.password = password
        self.account_type = account_type
        self.ws = None
        self.session_id = None
        self.connected = False

    async def connect(self):
        ssl_ctx = ssl.create_default_context()
        url = SERVERS[self.account_type]
        self.ws = await websockets.connect(
            url,
            ssl=ssl_ctx,
            ping_interval=30,
            ping_timeout=20,
            extra_headers=HEADERS,
            open_timeout=30
        )
        await self._login()
        self.connected = True
        logger.info("✅ Connecté à XTB XAPI")

    async def _login(self):
        cmd = {
            "command": "login",
            "arguments": {
                "userId": self.login,
                "password": self.password,
                "appId": "xStation5",
                "appName": "xStation"
            }
        }
        response = await self._send(cmd)
        if response.get("status") is True:
            self.session_id = response.get("streamSessionId")
            logger.info("✅ Login XTB réussi")
        else:
            raise Exception(f"❌ Login échoué: {response}")

    async def _send(self, command):
        await self.ws.send(json.dumps(command))
        response = await self.ws.recv()
        return json.loads(response)

    async def get_balance(self):
        return await self._send({"command": "getMarginLevel"})

    async def get_symbol(self, symbol):
        return await self._send({
            "command": "getSymbol",
            "arguments": {"symbol": symbol}
        })

    async def get_candles(self, symbol, period, count=100):
        import time
        start = int((time.time() - count * period * 60) * 1000)
        return await self._send({
            "command": "getChartLastRequest",
            "arguments": {
                "info": {"period": period, "start": start, "symbol": symbol}
            }
        })

    async def open_trade(self, symbol, cmd_type, volume, sl=None, tp=None, comment="BotTrade"):
        symbol_info = await self.get_symbol(symbol)
        if symbol_info.get("status") is not True:
            raise Exception(f"Symbole introuvable: {symbol}")
        record = symbol_info["returnData"]
        price = record["ask"] if cmd_type == 0 else record["bid"]
        return await self._send({
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": {
                    "cmd": cmd_type,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "sl": sl if sl else 0,
                    "tp": tp if tp else 0,
                    "type": 0,
                    "comment": comment
                }
            }
        })

    async def get_open_trades(self):
        return await self._send({
            "command": "getTrades",
            "arguments": {"openedOnly": True}
        })

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
        self.connected = False
