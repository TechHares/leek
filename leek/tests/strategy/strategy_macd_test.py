#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/26 10:59
# @Author  : shenglin.li
# @File    : strategy_macd_test.py
# @Software: PyCharm
import decimal
import unittest
from decimal import Decimal

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import JustFinishKData
from leek.strategy.strategy_macd import MacdReverseStrategy
from leek.tests.strategy.symbol_choose_test import draw_fig
from leek.trade.trade import PositionSide


class TestRoaminLoong1(unittest.TestCase):
    def testMacd1(self):
        from leek.strategy.strategy_macd import MacdStrategy

        strategy = MacdStrategy(5, 17, 60, 7)
        PositionRateManager.__init__(strategy, 0.5)
        workflow = ViewWorkflow(strategy, "5m", 1710000000000, 1710259200000, "ZRXUSDT")
        workflow.start()
        df = pd.DataFrame(workflow.kline_data)
        df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig = workflow.draw(fig=fig, df=df, row=1)
        # workflow.draw(fig=fig, df=df)

        df['avg_price'] = df['amount'] / df['volume']
        df['ma_fast'] = df['avg_price'].rolling(window=strategy.fast_line_period).mean().apply(lambda x: Decimal(x))
        df['ma_slow'] = df['avg_price'].rolling(window=strategy.slow_line_period).mean().apply(lambda x: Decimal(x))
        df['ma_long'] = df['avg_price'].rolling(window=strategy.long_line_period).mean().apply(lambda x: Decimal(x))
        # df['ma_fast'] = df['close'].rolling(window=5).mean().apply(lambda x: Decimal(x))
        # df['ma_slow'] = df['close'].rolling(window=17).mean().apply(lambda x: Decimal(x))
        # df['ma_long'] = df['close'].rolling(window=60).mean().apply(lambda x: Decimal(x))

        df['dif'] = df['ma_fast'] - df['ma_slow']
        df['dea'] = df['dif'].ewm(span=strategy.average_moving_period, adjust=False).mean().apply(lambda x: Decimal(x))
        df['m'] = df['dif'] - df['dea']
        # 添加 ma 指标
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'],
                                 mode='lines', name='dif', line=dict(color='black', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'],
                                 mode='lines', name='dea', line=dict(color='orange', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['m'],
                                 mode='lines', name='m', line=dict(color='green', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_fast'],
                                 mode='lines', name='ma_fast', line=dict(color='black', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_slow'],
                                 mode='lines', name='ma_slow', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_long'],
                                 mode='lines', name='ma_long', line=dict(color='red', width=1)), row=1, col=1)
        fig.show()


    def testMacd2(self):
        strategy = MacdReverseStrategy(fast_period=12, slow_period=26, moving_period=9, min_histogram_num=3)
        JustFinishKData.__init__(strategy, True)
        PositionRateManager.__init__(strategy, "1")
        PositionDirectionManager.__init__(strategy, PositionSide.FLAT)
        workflow = ViewWorkflow(strategy, "30m", "2024-09-21 14:30", "2024-10-10 18:30", "MAX-USDT-SWAP")
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        # df['direction'] = df['direction'].apply(lambda x: x.value == 1 if x else None)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['direction'], mode='lines', name='direction'), row=3, col=1)

        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif', line={"color": "black", "width": 1}),
            row=4, col=1)
        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea', line={"color": "orange", "width": 1}),
            row=4, col=1)
        fig.add_trace(
            go.Bar(x=df['Datetime'], y=df['histogram'], marker={"color": np.where(df['histogram'] > 0, 'green', 'red')},
                   name='His'), row=4, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        # 显示图表
        fig.show()

    def testMacd3(self):
        workflow = SymbolChooseWorkflow(MacdReverseStrategy, {
            "max_single_position": "1",
            "total_amount": "1000",
            "just_finish_k": True,
            "direction": "4",
            "stop_loss_rate": "0.03",

            "min_histogram_num": 9,
            "fast_period": 12,
            "slow_period": 26,
            "smoothing_period": 9,

            "atr_coefficient": "1.5",
        }, "15m", "2024-08-21 14:30", "2024-10-10 18:30")
        workflow.start(sort_func=draw_fig(f"macdre"))


if __name__ == '__main__':
    ...
