#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/12 01:27
# @Author  : shenglin.li
# @File    : symbol_choose_test.py
# @Software: PyCharm
import copy
import json
import unittest

from joblib import Parallel, delayed

from leek.common.utils import decimal_quantize
from leek.data import BacktestDataSource
from leek.runner.backtest import BacktestWorkflow
import warnings

warnings.simplefilter('ignore', ResourceWarning)


class TestSymbolChoose(unittest.TestCase):
    def setUp(self) -> None:
        self.data = {
            "strategy_data": {
                "name": "dow1", "total_amount": "1000.000000000000",
                "strategy_cls": "leek.strategy.strategy_dow_theory|DowV1Strategy",
                "symbol": "",
                "min_price": "0.000000", "max_price": "0.000000", "grid": "10",
                "risk_rate": "0.100000", "side": "1", "rolling_over": "1", "symbols": "",
                "direction": "4", "mean_type": "SMA", "window": "10", "threshold": "0.020000",
                "take_profit_rate": "0.200000", "fallback_percentage": "0.04",
                "max_single_position": "1", "stop_loss_rate": "180.000000", "num_std_dev": "2.00",
                "atr_coefficient": "1.000000", "fast_period": "5", "slow_period": "20",
                "long_period": "120", "smoothing_period": "9", "factory": "2", "price_type": "1",
                "open_channel": "20", "close_channel": "10", "true_range_window": "20",
                "expected_value": "0.010000", "add_position_rate": "0.500000",
                "close_position_rate": "2.000000", "open_vhf_threshold": "0.500000",
                "close_vhf_threshold": "0.000000", "take_profit_period": "10", "trade_type": "0",
                "win_loss_target": "1.500000", "data_source": "3", "trade": "2", "status": "1",
                "process_id": "0", "end_time_0": "2024/05/11", "end_time_1": "16:05",
                "initial-end_time_0": "2024/05/11", "initial-end_time_1": "16:05",
                "actionName": "actionValue"
            },
            "trader_data": {
                "slippage": 0,
                "fee_type": "2",
                "fee": 0.0005,
                "min_fee": 0,
                "limit_order_execution_rate": 100,
                "volume_limit": 4
            },
            "datasource": {
                "isIndeterminateSymbols": "true",
                "checkAllSymbols": "false",
                "interval": "4H",
                "symbols": ["FILUSDT"],
                "benchmark": "FILUSDT",
                "daterange": [1557760900479, 1715440900479],
                "start_time": 1557760900479,
                "end_time": 1715440900479
            }
        }
        self.symbols = BacktestDataSource("4h", [], 0, 0, "x").get_all_symbol()

    def test_dow1(self):
        profit = {}

        def run(args):
            x, d = args
            workflow = BacktestWorkflow(d)
            workflow.start()
            workflow.data_source.join()
            p = workflow.strategy.position_manager
            a = decimal_quantize(p.available_amount + p.freeze_amount + p.position_value)
            return x, a

        ws = []
        for symbol in self.symbols:
            self.data["datasource"]["benchmark"] = symbol
            self.data["datasource"]["symbols"][0] = symbol
            ws.append((symbol, copy.deepcopy(self.data)))
        results = Parallel(n_jobs=-1)(delayed(run)(task) for task in ws)
        print(results)

        print(sorted(results, key=lambda x: x[1], reverse=True)[:10])


if __name__ == '__main__':
    unittest.main()
    #
