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
from leek.strategy import BaseStrategy
from leek.data import BacktestDataSource, DataSource
from leek.strategy.common import SymbolsFilter, StopLoss, TakeProfit, FallbackTakeProfit
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager, CalculatorContainer
from leek.strategy.strategy_mean_reverting import MeanRevertingStrategy


class TestDemoClass(unittest.TestCase):
    def setUp(self):
        self.demo_class = MeanRevertingStrategy(mean_type="EMA",
                                                threshold="0.002")
        PositionRateManager.__init__(self.demo_class, "0.5")
        SymbolsFilter.__init__(self.demo_class, "BTCUSDT")
        PositionDirectionManager.__init__(self.demo_class)
        CalculatorContainer.__init__(self.demo_class)
        StopLoss.__init__(self.demo_class)
        TakeProfit.__init__(self.demo_class)
        FallbackTakeProfit.__init__(self.demo_class)
        self.bus = EventBus()
        BaseStrategy.__init__(self.demo_class, 1, self.bus,
                              decimal.Decimal("1000"))
        self.data = BacktestDataSource("1m", ["BTCUSDT"], 1692547200000, 1697817600000, "BTCUSDT")
        DataSource.__init__(self.data, self.bus)

    def test_handle(self):
        self.demo_class.symbols = None
        self.demo_class.post_constructor()
        self.data._run()


if __name__ == "__main__":
    unittest.main()
