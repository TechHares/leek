#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:19
# @Author  : shenglin.li
# @File    : data_okx.py
# @Software: PyCharm
import json
import threading
import time
from datetime import datetime
from decimal import Decimal

from okx import MarketData, PublicData

from leek.common import logger, G, config
from leek.common.utils import decimal_to_str
from leek.data.data import WSDataSource, DataSource


class OkxKlineDataSource(WSDataSource):
    verbose_name = "OKX K线"

    def __init__(self, work_flag="0", channels=[], symbols=""):
        ws_domain = "wss://ws.okx.com:8443/ws/v5/business"
        if work_flag == "1":
            ws_domain = "wss://wspap.okx.com:8443/ws/v5/business?brokerId=9999"
        if work_flag == "2":
            ws_domain = "wss://wsaws.okx.com:8443/ws/v5/business"
        self.domain = "https://www.okx.com"
        self.flag = "0"
        if work_flag == "1":
            self.flag = "1"
        if work_flag == "2":
            self.domain = "https://aws.okx.com"
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

    def data_init_hook(self, params) -> list:
        logger.info("OkxKlineDataSource 初始化：%s" % json.dumps(params, default=decimal_to_str))
        if params is None:
            return []
        api = MarketData.MarketAPI(domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)
        symbol = params["symbol"]
        interval = params["interval"].replace("h", "H").replace("w", "W").replace("d", "D")
        limit = min(100, params["size"])
        ts = int(time.time() * 1000)
        res = []
        while len(res) < params["size"]:
            candlesticks = api.get_history_candlesticks(instId=symbol, bar=interval, limit=limit, after=ts)
            for row in candlesticks["data"]:
                data = G(symbol=params["symbol"],
                         interval=params["interval"],
                         timestamp=int(row[0]),
                         open=Decimal(row[1]),
                         high=Decimal(row[2]),
                         low=Decimal(row[3]),
                         close=Decimal(row[4]),
                         volume=Decimal(row[5]),
                         amount=Decimal(row[7]),
                         finish=int(row[8])
                         )
                ts = int(row[0]) - 1
                res.append(data)

        res = res[:params["size"]]
        res.reverse()
        return res

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
        logger.debug(f"OKX数据源：{msg}")
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
        self.api = MarketData.MarketAPI(domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)
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


class OKXFundingDataSource(DataSource):
    verbose_name = "OKX资金费"

    def __init__(self, interval=300, work_flag="0"):
        """
        行情数据
        :param interval: 获取数据间隔(秒)
        :param work_flag: 0 实盘 1 模拟盘 2 aws实盘
        """
        self.interval = interval
        self.flag = "0"
        self.domain = "https://www.okx.com"
        if work_flag == "1":
            self.flag = "1"
        if work_flag == "2":
            self.domain = "https://aws.okx.com"
        self.market_api = MarketData.MarketAPI(domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)
        self.public_api = PublicData.PublicAPI(domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)
        self.__run = True

    def _run(self):
        next_trigger = 0
        while self.__run:
            if int(time.time()) < next_trigger:
                time.sleep(1)
                continue
            tickers = self.market_api.get_tickers(instType="SWAP")
            if tickers and tickers["code"] == "0":
                tickers = tickers["data"]
            else:
                logger.error("获取所有市场数据失败")
                continue
            next_trigger = int(time.time()) + self.interval
            symbols = set([ticker["instId"] for ticker in tickers if ticker["instId"].endswith("-USDT-SWAP")])
            funding_rates = []
            for symbol in symbols:
                res = self.public_api.get_funding_rate(symbol)
                if res and res["code"] == "0":
                    funding_rates.append(G(**res["data"][0]))
                else:
                    logger.error(f"获取{symbol}资金费数据失败")
            a = sorted(funding_rates, key=lambda x: abs(Decimal(x.fundingRate)), reverse=True)[:10]
            swaps = []
            spots = []
            for s in a:
                print(s.instId)
            data = G(symbol="funding",
                     timestamp=int(datetime.now().timestamp() * 1000),
                     rates=a,
                     finish=1
                     )
            self._send_tick_data(data)


if __name__ == '__main__':
    pass
