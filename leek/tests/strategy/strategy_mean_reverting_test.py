#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:02
# @Author  : shenglin.li
# @File    : strategy_mean_reverting.py
# @Software: PyCharm
import decimal
import unittest
from datetime import datetime
from typing import Any

from leek.common import EventBus
from leek.strategy import MeanRevertingStrategy, BaseStrategy
from leek.data import BacktestDataSource, DataSource


class TestDemoClass(unittest.TestCase):
    def setUp(self):
        self.demo_class = MeanRevertingStrategy(symbols="BTCUSDT", direction="4", mean_type="EMA", lookback_intervals=10,
                                                threshold="0.002", take_profit_rate="0.03", stop_loss_rate="0.02",
                                                fallback_percentage="0.008", max_single_position="0.5")
        self.bus = EventBus()
        BaseStrategy.__init__(self.demo_class, 1, self.bus,
                              decimal.Decimal("1000"))
        self.data = BacktestDataSource("1m", ["BTCUSDT"], 1692547200000, 1697817600000, "BTCUSDT")
        DataSource.__init__(self.data, self.bus)

    def test_handle(self):
        self.demo_class.symbols = None
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.demo_class.handle)
        self.data._run()


if __name__ == "__main__":
    unittest.main()
