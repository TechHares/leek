#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/04 21:40
# @Author  : shenglin.li
# @File    : strategy_area_test.py
# @Software: PyCharm
import unittest

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.strategy.strategy_area import AreaStrategy
from leek.trade.trade import PositionSide


class TestArea(unittest.TestCase):
    def test_handle(self):
        self.strategy = AreaStrategy()

        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        DynamicRiskControl.__init__(self.strategy, 13, "1.3", "0.02")
        self.bus = EventBus()

        # workflow = ViewWorkflow(self.strategy, "1d", "2021-01-01", "2024-02-28", "000300", 1)
        workflow = ViewWorkflow(self.strategy, "15m", "2024-03-15", "2024-05-24", "BLOCK-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "15m", "2020-03-15", "2024-05-24", "BTC-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        # df["benchmark"] = df["close"] / df.iloc[1]["close"]
        # df["profit"] = df["balance"] / decimal.Decimal("1000")
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['area'], mode='lines', name='area'), row=2, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', name='k'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines', name='d'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['j'], mode='lines', name='j'), row=3, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=True, row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        # fig.show()


if __name__ == '__main__':
    unittest.main()
