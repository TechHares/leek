#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/14 20:16
# @Author  : shenglin.li
# @File    : strategy_roamin_loong2_test.py
# @Software: PyCharm
import decimal
import unittest

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.common import EventBus, G, logger
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import JustFinishKData, StopLoss
from leek.strategy.strategy_roaming_loong import RoamingLoong1Strategy, AbcRoamingLoongStrategy, RoamingLoong2Strategy
from leek.tests.strategy.symbol_choose_test import draw_fig
from leek.trade.trade import PositionSide


class TestRoaminLoong1(unittest.TestCase):

    def test_handle(self):
        # logger.setLevel("DEBUG")
        strategy = RoamingLoong2Strategy(window=14, period=14, k_smoothing_factor=3, d_smoothing_factor=3, fast_period=14,
                                         slow_period=30, smoothing_period=16, k_num=9, min_histogram_num=9, position_num=3, open_change_rate="0.01",
                                         close_change_rate="0.01", peak_over_sell=5, over_sell=20, peak_over_buy=95, over_buy=80,
                                         close_position_when_direction_change=False)
        JustFinishKData.__init__(strategy, True)
        StopLoss.__init__(strategy, "0.05")
        PositionRateManager.__init__(strategy, "1")
        PositionDirectionManager.__init__(strategy, PositionSide.FLAT)
        workflow = ViewWorkflow(strategy, "5m", "2024-09-21 14:30", "2024-10-24 18:30", "ULTI-USDT-SWAP")
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        df['direction'] = df['direction'].apply(lambda x: x.value == 1 if x and isinstance(x, PositionSide) else x)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['direction'], mode='lines', name='profit'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines',
                                 line=dict(color='black', width=1), name='k'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines',
                                 line=dict(color='orange', width=1), name=''), row=4, col=1)

        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif', line={"color": "black", "width": 1}),
            row=5, col=1)
        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea', line={"color": "orange", "width": 1}),
            row=5, col=1)
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['histogram'], marker={"color": np.where(df['histogram'] > 0, 'green', 'red')}, name='His'), row=5, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        # 显示图表
        fig.show()

    def test_handle2(self):
        k_nums = [9]
        min_histogram_nums = [12]
        position_nums = [3]
        for k_num in k_nums:
            for min_histogram_num in min_histogram_nums:
                for position_num in position_nums:
                    workflow = SymbolChooseWorkflow(RoamingLoong2Strategy, {
                        "max_single_position": "1",
                        "total_amount": "1000",
                        "just_finish_k": True,
                        "direction": "4",
                        "stop_loss_rate": "0.05",

                        "window": 14,
                        "period": 14,
                        "k_smoothing_factor": 3,
                        "d_smoothing_factor": 3,

                        "fast_period": 14,
                        "slow_period": 30,
                        "smoothing_period": 10,

                        "k_num": k_num,
                        "min_histogram_num": min_histogram_num,

                        "position_num": position_num,
                        "open_change_rate": "0.008",
                        "close_change_rate": "0.006",
                        "peak_over_sell": 4,
                        "peak_over_buy": 96,
                        "over_sell": 20,
                        "over_buy": 80,
                        "close_position_when_direction_change": "true",
                    }, "5m", "2024-10-05 14:30", "2024-10-15 18:30", [])
                    workflow.start(sort_func=draw_fig(f"loong, k_num={k_num}, min_histogram_num={min_histogram_num}, position_num={position_num}"))



if __name__ == '__main__':
    pass
