#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/12 01:27
# @Author  : shenglin.li
# @File    : symbol_choose_test.py
# @Software: PyCharm
import copy
import statistics
import unittest
import warnings

import numpy as np
from joblib import Parallel, delayed

from leek.common.utils import decimal_quantize
from leek.runner.backtest import BacktestWorkflow
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.strategy.strategy_bollinger_bands import BollingerBandsV2Strategy
from leek.strategy.strategy_dow_theory import DowV1Strategy
from leek.strategy.strategy_td import TDStrategy
import pandas as pd

warnings.simplefilter('ignore', ResourceWarning)


def draw_profit_and_drawdown(memo, results):
    import plotly.graph_objs as go
    symbols = []
    profits = []
    max_drawdowns = []
    for res in results:
        symbol = res[0]
        res = res[1]
        b, s, x = zip(*res)
        profit_rate = np.array(list(s)) / s[0]
        cumulative_max = np.maximum.accumulate(profit_rate)
        drawdowns = (cumulative_max - profit_rate) / cumulative_max
        max_drawdown = np.max(drawdowns)
        symbols.append(symbol)
        profits.append(profit_rate[-1])
        max_drawdowns.append(max_drawdown)

    # 创建利润散点图
    profit_trace = go.Scatter(x=symbols, y=profits, mode='markers',
                              name='利润(%s/%s)' % (len([p for p in profits if p > 1]), len(profits)),
                              marker=dict(color='green'))

    # 创建最大回撤散点图
    drawdown_trace = go.Scatter(x=symbols, y=max_drawdowns, mode='markers', name='最大回撤',
                                marker=dict(color='red'))

    # 计算中位数
    median_profit = statistics.median(profits)
    mean_profit = statistics.mean(profits)
    median_drawdown = statistics.median(max_drawdowns)
    mean_drawdown = statistics.mean(max_drawdowns)

    # 创建中位数的水平线
    balance_line = go.Scatter(x=symbols, y=[1] * len(symbols), mode='lines',
                              name='成本线',
                              marker=dict(color='orange'))

    # 创建中位数的水平线
    median_line_drawdown = go.Scatter(x=symbols, y=[median_drawdown] * len(symbols), mode='lines',
                                      name='回撤中位数: %s' % median_drawdown,
                                      marker=dict(color='red'))
    mean_drawdown_line = go.Scatter(x=symbols, y=[mean_drawdown] * len(symbols), mode='lines',
                                    name='回撤均值: %s' % mean_drawdown,
                                    marker=dict(color='black'))

    median_line_profit = go.Scatter(x=symbols, y=[median_profit] * len(symbols), mode='lines',
                                    name='利润中位数: %s' % median_profit,
                                    marker=dict(color='blue'))
    mean_profit_line = go.Scatter(x=symbols, y=[median_profit] * len(symbols), mode='lines',
                                  name='利润均值: %s' % mean_profit,
                                  marker=dict(color='gray'))

    # 创建布局
    layout = go.Layout(title='%s' % memo, xaxis=dict(title='Symbol'),
                       yaxis=dict(title='Value'),
                       font=dict(family='Arial Unicode MS, sans-serif'),
                       showlegend=True)

    # 创建图表
    fig = go.Figure(data=[median_line_profit, mean_profit_line, median_line_drawdown,
                          mean_drawdown_line, balance_line, profit_trace, drawdown_trace], layout=layout)

    # 显示图表
    fig.show()


def draw_fig(memo=""):
    def __draw_fig(results):
        results = [x for x in results if len(x[1]) > 0]
        r = sorted(results, key=lambda x: x[1][-1][1], reverse=True)
        draw_profit_and_drawdown(memo, r)
        r = r[:20]
        r = [x for x in r if x[1][-1][1] > 1000]
        print([(x[0], x[1][-1][1]) for x in r])
        print(",".join([x[0] for x in r]))
        return r

    return __draw_fig


class TestSymbolChoose(unittest.TestCase):

    def test_dow1(self):
        workflow = SymbolChooseWorkflow(DowV1Strategy, {
            "max_single_position": "1",
            "total_amount": "1000",
            "open_channel": 20,
            "close_channel": 10,
            "long_period": 120,
            "win_loss_target": "1.3",
            "half_needle": True,
            "just_finish_k": True,
            "trade_type": 0,
            "direction": "4",
            "atr_coefficient": "1.5",
            "stop_loss_rate": "0.03",

        }, "1h", "2024-05-10", "2024-05-27")
        workflow.start(sort_func=draw_fig("1h"))
        # workflow.start()

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

        }, "1d", "2023-05-25", "2024-05-26")
        workflow.start(draw_fig("1h"))

    def test_bollv2(self):
        # for i in ["30m", "1h"]:
        for i in ["30m"]:
            # workflow = SymbolChooseWorkflow(BollingerBandsV2Strategy, {
            #     "max_single_position": "1",
            #     "total_amount": "1000",
            #     "just_finish_k": True,
            #     "direction": "4",
            #
            #     "num_std_dev": "3",
            #     "window": 18,
            #     "fast_period": 10,
            #     "slow_period": 20,
            #     "smoothing_period": 7,
            #
            #     "atr_coefficient": "1.5",
            #     "stop_loss_rate": "0.02",
            #
            # }, "15m", "2024-04-25", "2024-05-27")
            workflow = SymbolChooseWorkflow(BollingerBandsV2Strategy, {
                "max_single_position": "1",
                "total_amount": "1000",
                "just_finish_k": True,
                "direction": "4",

                "num_std_dev": "3",
                "window": 18,
                "fast_period": 10,
                "slow_period": 20,
                "smoothing_period": 7,

                "atr_coefficient": "1.5",
                "stop_loss_rate": "0.02",

            }, "30m", "2024-04-25", "2024-05-27")

            # workflow = SymbolChooseWorkflow(BollingerBandsV2Strategy, {
            #     "max_single_position": "1",
            #     "total_amount": "1000",
            #     "just_finish_k": True,
            #     "direction": "4",
            #
            #     "window": 20,
            #     "num_std_dev": "2",
            #     "fast_period": 12,
            #     "slow_period": 26,
            #     "smoothing_period": 9,
            #
            #     "atr_coefficient": "1.5",
            #     "stop_loss_rate": "0.05",
            #
            # }, i, "2024-03-25", "2024-05-26")
            workflow.start(sort_func=draw_fig("%s 不仿真" % i))
        # gal sui lsk gmt wif mew tia


if __name__ == '__main__':
    unittest.main()
