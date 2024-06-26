#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 21:27
# @Author  : shenglin.li
# @File    : strategy_grid_test.py
# @Software: PyCharm
import datetime
import time
import unittest
from decimal import Decimal

import pandas as pd
from plotly.subplots import make_subplots

from leek.common.utils import DateTime
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.strategy.common import SymbolFilter, PositionSideManager
from leek.strategy.strategy_bollinger_bands import BollingerBandsV2Strategy
from leek.strategy.strategy_grid import SingleGridStrategy, RSIGridStrategy
from leek.tests.strategy.symbol_choose_test import draw_fig
from leek.trade.trade import PositionSide
import plotly.graph_objs as go


class TestGridStrategy(unittest.TestCase):
    def test_grid(self):
        self.strategy = SingleGridStrategy(min_price="1.2", max_price="1.4", risk_rate=0.1, grid=10)

        SymbolFilter.__init__(self.strategy, "TNSR-USDT-SWAP")
        PositionSideManager.__init__(self.strategy, PositionSide.SHORT)
        workflow = ViewWorkflow(self.strategy, "1m", "2024-06-03 15:00", "2024-06-03 21:44", "TNSR-USDT-SWAP")
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        # to_dict = self.strategy.to_dict()
        # print(to_dict)
        print(len(df))
        fig.show()

    def test_(self):
        sz = Decimal("64")
        sz *= Decimal("0.1") / Decimal("0.9")
        print(sz)

    def test_rsigrid(self):
        # self.strategy = RSIGridStrategy(over_buy=90, over_sell=10)
        self.strategy = RSIGridStrategy(over_buy=60, over_sell=40)

        SingleGridStrategy.__init__(self.strategy, min_price="2.5", max_price="3.2", risk_rate=0.05, grid=25)
        SymbolFilter.__init__(self.strategy, "ZRO-USDT-SWAP")
        PositionSideManager.__init__(self.strategy, PositionSide.SHORT)
        workflow = ViewWorkflow(self.strategy, "1m", "2024-06-23 01:00", "2024-06-25 00:00", "ZRO-USDT-SWAP")
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines',
                                 line=dict(color='black', width=1), name='k'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines',
                                 line=dict(color='orange', width=1), name=''), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        # to_dict = self.strategy.to_dict()
        # print(to_dict)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
