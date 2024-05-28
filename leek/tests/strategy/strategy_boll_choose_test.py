#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:27
# @Author  : shenglin.li
# @File    : strategy_boll_choose_test.py
# @Software: PyCharm
import datetime
import time
import unittest

from leek.common.utils import DateTime
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.strategy.strategy_bollinger_bands import BollingerBandsV2Strategy
from leek.tests.strategy.symbol_choose_test import draw_fig


class TestBollSymbolChoose(unittest.TestCase):
    arg_num_std_dev = ["1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5"]
    arg_window = [15, 18, 20, 22, 25, 28, 30]
    arg_fast_period = [5, 7, 10, 12, 15, 20]
    arg_slow_period = [14, 18, 20, 25, 26, 30]
    arg_smoothing_period = [5, 7, 9, 11]
    arg_interval = ["15m", "30m", "1h", "4h"]

    def test_bollv2(self):
        timestamp = datetime.datetime.now().timestamp()
        start = DateTime.to_date_str(timestamp * 1000 - 30 * 24 * 60 * 60 * 1000, DateTime.PATTERN_DATE)
        end = DateTime.to_date_str(timestamp * 1000, DateTime.PATTERN_DATE)
        if timestamp > 1:
            print(start, end)
            return
        for num_std_dev in self.arg_num_std_dev:
            for window in self.arg_window:
                for fast_period in self.arg_fast_period:
                    for slow_period in self.arg_slow_period:
                        for smoothing_period in self.arg_smoothing_period:
                            for interval in self.arg_interval:
                                workflow = SymbolChooseWorkflow(BollingerBandsV2Strategy, {
                                    "max_single_position": "1",
                                    "total_amount": "1000",
                                    "just_finish_k": True,
                                    "direction": "4",

                                    "num_std_dev": num_std_dev,
                                    "window": window,
                                    "fast_period": fast_period,
                                    "slow_period": slow_period,
                                    "smoothing_period": smoothing_period,

                                    "atr_coefficient": "1.5",
                                    "stop_loss_rate": "0.02",

                                }, interval, start, end)
                                workflow.start(sort_func=draw_fig(f"boll_v2_{interval}(num_std_dev={num_std_dev},"
                                                                  f"window={window},fast_period={fast_period},"
                                                                  f"slow_period={slow_period},"
                                                                  f"smoothing_period={smoothing_period})"))



if __name__ == '__main__':
    unittest.main()
