#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/12 01:27
# @Author  : shenglin.li
# @File    : symbol_choose_test.py
# @Software: PyCharm
import copy
import unittest
import warnings

from joblib import Parallel, delayed

from leek.common.utils import decimal_quantize
from leek.runner.backtest import BacktestWorkflow
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.strategy.strategy_dow_theory import DowV1Strategy
from leek.strategy.strategy_td import TDStrategy

warnings.simplefilter('ignore', ResourceWarning)


class TestSymbolChoose(unittest.TestCase):

    def test_dow1(self):
        workflow = SymbolChooseWorkflow(DowV1Strategy, {
            "max_single_position": "1",
            "total_amount": "1000",
            "open_channel": 20,
            "close_channel": 7,
            "long_period": 240,
            "win_loss_target": "1.5",
            "half_needle": False,
            "just_finish_k": False,
            "trade_type": 0,
            "fallback_percentage": "0.05",
            "direction": "4",
            "atr_coefficient": "1.3",
            "stop_loss_rate": "0.02",

        }, "30m", "2024-05-18", "2024-05-26")
        workflow.start()

    def test_td(self):
        workflow = SymbolChooseWorkflow(TDStrategy, {
            "max_single_position": "1",
            "total_amount": "1000",
            "just_finish_k": True,
            "direction": "4",
            "window": 4,
            "fast_period": 4,
            "slow_period": 4,
            "atr_coefficient": "1.3",
            "stop_loss_rate": "0.02",

        }, "30m", "2024-05-25", "2024-05-26")
        workflow.start()


if __name__ == '__main__':
    unittest.main()
