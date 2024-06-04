#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/7 22:40
# @Author  : shenglin.li
# @File    : strategy_turtle_test.py
# @Software: PyCharm
import decimal
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.t import KDJ
from leek.trade.trade import PositionSide


class TestKDJ(unittest.TestCase):
    def test_handle(self):
        workflow = ViewWorkflow(None, "1d", "2024-02-05", "2024-06-04", "000300", 1)
        # workflow = ViewWorkflow(self.strategy, "15m", "2024-03-15", "2024-05-24", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")
        data = workflow.get_data("000300")
        kdj = KDJ()
        for d in data:
            r = kdj.update(d)
            if r:
                d.k, d.d, d.j = r
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', name='k'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines', name='d'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['j'], mode='lines', name='j'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
