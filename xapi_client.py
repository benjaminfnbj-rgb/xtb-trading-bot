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

class XAPIClient:
    def __init__(self, login, password, account_type="real"):
        self.login = login
        self.password = password
        self.account_type = account_type
        self.ws = None
        self.stream_ws = None
        self.session_id = None
        self.connected = False

    async def connect(self):
        ssl_ctx = ssl.create_default_context()
        url = SERVERS[self.account_type]
        self.ws = await websockets.connect(url, ssl=ssl_ctx, ping_interval=30)
        await self._login()
        self.connected = True
        logger.info("✅ Connecté à XTB XAPI")

    async def _login(self):
        cmd = {
            "command": "login",
            "arguments": {
                "userId": self.login,
                "password": self.password,
                "appId": "trading_bot",
                "appName": "BenjaminBot"
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
        cmd = {"command": "getMarginLevel"}
        return await self._send(cmd)

    async def get_symbol(self, symbol):
        cmd = {
            "command": "getSymbol",
            "arguments": {"symbol": symbol}
        }
        return await self._send(cmd)

    async def get_candles(self, symbol, period, count=100):
        import time
        start = int((time.time() - count * period * 60) * 1000)
        cmd = {
            "command": "getChartLastRequest",
            "arguments": {
                "info": {
                    "period": period,
                    "start": start,
                    "symbol": symbol
                }
            }
        }
        return await self._send(cmd)

    async def open_trade(self, symbol, cmd_type, volume, sl=None, tp=None, comment="BotTrade"):
        symbol_info = await self.get_symbol(symbol)
        if symbol_info.get("status") is not True:
            raise Exception(f"Symbole introuvable: {symbol}")

        record = symbol_info["returnData"]
        price = record["ask"] if cmd_type == 0 else record["bid"]  # 0=BUY, 1=SELL

        trade_cmd = {
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": {
                    "cmd": cmd_type,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "sl": sl if sl else 0,
                    "tp": tp if tp else 0,
                    "type": 0,  # OPEN
                    "comment": comment
                }
            }
        }
        return await self._send(trade_cmd)

    async def close_trade(self, order_id, symbol, cmd_type, volume, price):
        close_cmd = {
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": {
                    "cmd": cmd_type,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": 2,  # CLOSE
                    "order": order_id,
                    "comment": "CloseBot"
                }
            }
        }
        return await self._send(close_cmd)

    async def get_open_trades(self):
        cmd = {"command": "getTrades", "arguments": {"openedOnly": True}}
        return await self._send(cmd)

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
        self.connected = False
