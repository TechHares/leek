#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:19
# @Author  : shenglin.li
# @File    : data_okx.py
# @Software: PyCharm
import json
import threading
import time
from decimal import Decimal

from okx import MarketData

from leek.common import logger, G, EventBus
from leek.data.data import WSDataSource, DataSource


class OkxKlineDataSource(WSDataSource):
    verbose_name = "OKX K线"

    def __init__(self, work_flag="0", channels=[], symbols=""):
        ws_domain = "wss://ws.okx.com:8443/ws/v5/business"
        if work_flag == "1":
            ws_domain = "wss://wspap.okx.com:8443/ws/v5/business?brokerId=9999"
        if work_flag == "2":
            ws_domain = "wss://wsaws.okx.com:8443/ws/v5/business"
        WSDataSource.__init__(self)
        self.url = ws_domain
        self.channels = []
        for symbol in symbols.split(","):
            for channel in channels:
                self.channels.append({
                    "channel": "candle" + channel,
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


class OkxMarketDataSource(DataSource):
    verbose_name = "OKX 行情"
    """
    只有收盘价有效，其它K线相关的数据无法获取， 对应值含义不一样
    """
    __inst_type = ["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION"]

    def __init__(self, inst_type, interval=300, work_flag="0"):
        """
        行情数据
        :param inst_type: 产品类型
        :param interval: 获取数据间隔(秒)
        :param work_flag: 0 实盘 1 模拟盘 2 aws实盘
        """
        self.inst_type = inst_type
        self.interval = interval
        self.flag = "0"
        self.domain = "https://www.okx.com"
        if work_flag == "1":
            self.flag = "1"
        if work_flag == "2":
            self.domain = "https://aws.okx.com"
        self.api = MarketData.MarketAPI(domain=self.domain, flag=self.flag, debug=False)
        self.__run = True

    def _run(self):
        next_trigger = 0
        while self.__run:
            if int(time.time()) < next_trigger:
                time.sleep(1)
                continue
            next_trigger = int(time.time()) + self.interval
            tickers = self.api.get_tickers(instType=self.inst_type)
            if tickers and tickers["code"] == "0":
                for ticker in tickers["data"]:
                    if ticker["instId"].endswith("-USDT-" + self.inst_type):
                        data = G(symbol=ticker["instId"],
                                 timestamp=int(ticker["ts"]),
                                 open=Decimal(ticker["last"]),
                                 high=Decimal(ticker["last"]),
                                 low=Decimal(ticker["last"]),
                                 close=Decimal(ticker["last"]),
                                 volume=Decimal(ticker["vol24h"]),
                                 amount=Decimal(ticker["volCcy24h"]),
                                 finish=1
                                 )
                        self._send_tick_data(data)

    def shutdown(self):
        super().shutdown()
        self.__run = False


if __name__ == '__main__':
    pass
