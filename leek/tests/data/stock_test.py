#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/9 19:25
# @Author  : shenglin.li
# @File    : stock_test.py
# @Software: PyCharm
import time
import unittest

from leek.common import EventBus
from leek.data import DataSource
from leek.data.data_backtest import StockBacktestDataSource, BacktestDataSource


class TestBase(unittest.TestCase):

    def test_stock(self):
        source = StockBacktestDataSource()
        bus = EventBus()
        DataSource.__init__(source, bus)
        BacktestDataSource.__init__(source, "1d", ["南方恒生科技", "000063"], 1609459200000, 1703337300000)
        # BacktestDataSource.__init__(source, "1d", "南方恒生科技", 1609459200000, 1703337300000)
        bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: print(x))
        source.start()
        time.sleep(100)
        source.shutdown()



if __name__ == '__main__':
    unittest.main()
