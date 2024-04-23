#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/19 23:16
# @Author  : shenglin.li
# @File    : strategy_roamin_loong1_test.py
# @Software: PyCharm
import decimal
import unittest

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.common import EventBus, G
from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.strategy_roaming_loong import RoamingLoong1Strategy, AbcRoamingLoongStrategy


class TestRoaminLoong1(unittest.TestCase):
    def setUp(self):
        self.strategy = RoamingLoong1Strategy()
        PositionRateManager.__init__(self.strategy, "1")
        AbcRoamingLoongStrategy.__init__(self.strategy)
        self.bus = EventBus()
        BaseStrategy.__init__(self.strategy, "V0", self.bus, decimal.Decimal("1000"))

    def test_handle(self):
        # workflow = ViewWorkflow(self.strategy, "5m", 1710000000000, 1710259200000, "ZRXUSDT")
        workflow = ViewWorkflow(self.strategy, "5m", 1701360000000, 1711814400000, "ZRXUSDT")

        # 添加超级趋势线
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        df['Trend Direction'] = np.where(df['close'] > df['st_trend'].shift(1), 'Up', 'Down')

        df['volatility'] = df['close'].rolling(window=20).std().apply(lambda x: decimal.Decimal(x)) / df['close']
        df['volatility_ma'] = df['volatility'].rolling(window=10).mean()

        # 根据趋势方向设置颜色
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['st_trend'], mode='lines', name='SuperTrend'), row=1, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['smiio_erg'], mode='lines', name='ERG'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['smiio_sig'], mode='lines', name='SIG'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['smiio_osc'], mode='lines', name='OSC'), row=2, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['volatility'], mode='lines', name='VOLATILITY'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['volatility_ma'], mode='lines', name='VOLATILITY_MA'), row=3, col=1)
        # fig.add_trace(go.Bar(x=df['Datetime'], y=df['smiio_osc'], width=1, name='OSC', marker=dict(
        #     color=df['smiio_osc'].apply(lambda x: 'rgba(255, 0, 0, 0.8)' if x > 0 else 'rgba(0, 0, 255, 0.8)'))),
        #               row=2, col=1)

        # fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        # 显示图表
        fig.show()
        # self.strategy._refresh_pool(data, G())


if __name__ == '__main__':
    pass
