#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:19
# @Author  : shenglin.li
# @File    : data_okx.py
# @Software: PyCharm
import json
import threading
from decimal import Decimal

from leek.common import logger, G
from leek.data.data import WSDataSource


class OkxKlineDataSource(WSDataSource):
    def __init__(self, channels=[], symbols=""):
        self.channels = []
        for symbol in symbols.split(","):
            for channel in channels:
                self.channels.append({
                    "channel": "candle"+channel,
                    "instId": symbol
                })
        self.timer = None

    def ping(self):
        if self.ws.keep_running:
            self.ws.send("ping")
            self.timer = threading.Timer(25, self.ping)
            self.timer.start()

    def on_open(self, ws):
        self.send_to_ws({"op": "subscribe", "args": self.channels})
        self.ping()

    def on_message(self, ws, message):
        if message == "pong":
            return

        msg = json.loads(message)
        if "event" in msg and (msg["event"] == "subscribe" or msg["event"] == "unsubscribe"):
            return
        logger.info(f"OKX数据源：{msg}")
        interval = msg["arg"]["channel"].replace("candle", "")
        symbol = msg["arg"]["instId"]
        if msg["data"]:
            for d in msg["data"]:
                data = G(symbol=symbol,
                         interval=interval,
                         timestamp=int(d[0]),
                         open=Decimal(d[1]),
                         high=Decimal(d[2]),
                         low=Decimal(d[3]),
                         close=Decimal(d[4]),
                         volume=Decimal(d[5]),
                         amount=Decimal(d[7]),
                         finish=int(d[8])
                         )
                self._send_tick_data(data)

    def shutdown(self):
        super().shutdown()
        if self.timer:
            self.timer.cancel()


if __name__ == '__main__':
    def p(d):
        print("收到：", d)


    ok = OkxKlineDataSource(p, "wss://ws.okx.com:8443/ws/v5/business",
                            [{"channel": "3m", "instId": "BTC-USDT-SWAP", "interval": "3m"},
                             {"channel": "3m", "instId": "ETH-USDT-SWAP", "interval": "3m"}])
    ok.start()
