#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/25 10:36
# @Author  : shenglin.li
# @File    : okx_test.py
# @Software: PyCharm
import time
import unittest
from datetime import datetime

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
        source = OkxKlineDataSource("2", ["1m"], "AEVO-USDT-SWAP")
        bus = EventBus()
        DataSource.__init__(source, bus)

        pre = None
        def check_data(x):
            nonlocal pre, source
            if x.finish == 1:
                if pre is None:
                    pre = x
                elif pre.timestamp == x.timestamp:
                    pre = None
                else:
                    print(DateTime.to_date_str(pre.timestamp), DateTime.to_date_str(x.timestamp))
                    source.shutdown()
            else:
                if pre is None or pre.timestamp == x.timestamp:
                    pre = x
                else:
                    print(DateTime.to_date_str(pre.timestamp), DateTime.to_date_str(x.timestamp))
                    source.shutdown()

        bus.subscribe(EventBus.TOPIC_TICK_DATA, check_data)
        source._run()
        print("shutdown")
        time.sleep(30)
        print("shutdown")
        source.shutdown()
        print("shutdown")
        time.sleep(30)

    def test_kline1(self):
        source = OkxKlineDataSource("2", ["5m"], "DYDX-USDT-SWAP,")
        bus = EventBus()
        DataSource.__init__(source, bus)
        datas = source.data_init_hook({k: v for k, v in zip(["symbol", "interval", "size"], ["DYDX-USDT-SWAP", "5m", 120])})
        for data in datas:
            print(datetime.fromtimestamp(data.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S"), data)

    def test_funding(self):
        source = OKXFundingDataSource()
        source._run()
        # kline = source.get_kline("BTC-USDT")
        # for k in kline:
        #     print(DateTime.to_date_str(k[0]), k[1], k[2])


if __name__ == '__main__':
    unittest.main()
