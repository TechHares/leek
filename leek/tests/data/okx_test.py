#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/25 10:36
# @Author  : shenglin.li
# @File    : okx_test.py
# @Software: PyCharm
import time
import unittest
from datetime import datetime

import ccxt

from leek.common import EventBus
from leek.common.utils import DateTime
from leek.data import DataSource, WSDataSource
from leek.data.data_okx import OkxMarketDataSource, OkxKlineDataSource, OKXFundingDataSource


class TestBase(unittest.TestCase):

    def test_market(self):
        source = OkxMarketDataSource("SWAP", 20, "2")
        bus = EventBus()
        DataSource.__init__(source, bus)
        bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: print(x))
        source._run()
        source.start()
        print("shutdown")
        time.sleep(30)
        print("shutdown")
        source.shutdown()
        print("shutdown")
        time.sleep(30)

    def test_kline(self):
        source = OkxKlineDataSource("1", ["5m"], "BTC-USDT-SWAP")
        bus = EventBus()
        DataSource.__init__(source, bus)
        source.start()
        bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: print(x))
        print("shutdown")
        time.sleep(30)
        print("shutdown")
        source.shutdown()
        print("shutdown")
        time.sleep(30)

    def test_kline1(self):
        source = OkxKlineDataSource("1", ["5m"], "BTC-USDT-SWAP")
        bus = EventBus()
        DataSource.__init__(source, bus)
        datas = source.data_init_hook(["BTC-USDT-SWAP", "4h", 120])
        for data in datas:
            print(datetime.fromtimestamp(data.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S"), data)

    def test_funding(self):
        source = OKXFundingDataSource()
        source._run()
        # kline = source.get_kline("BTC-USDT")
        # for k in kline:
        #     print(DateTime.to_date_str(k[0]), k[1], k[2])

    def test_cctx(self):
        okx = ccxt.okx({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",
                "fetchMarkets": ["swap"]
            }
        })

        markets = okx.fetch_markets({"instType": "SWAP", "instId": "BTC-USDT-SWAP"})
        print(markets[0]["info"])


if __name__ == '__main__':
    unittest.main()
