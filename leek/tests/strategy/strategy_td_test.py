#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/7 22:40
# @Author  : shenglin.li
# @File    : strategy_td_test.py
# @Software: PyCharm
import decimal
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_td import TDStrategy, TDSeqStrategy
from leek.tests.strategy.symbol_choose_test import draw_fig
from leek.trade.trade import PositionSide


class TestTD(unittest.TestCase):
    def test_handle(self):
        self.strategy = TDStrategy(4, 4, 4)

        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        self.bus = EventBus()

        workflow = ViewWorkflow(self.strategy, "1d", "2006-01-01", "2024-02-28", "000300", 1)
        # workflow = ViewWorkflow(self.strategy, "15m", "2024-03-15", "2024-05-24", "BLOCK-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "1h", "2022-03-15", "2024-05-24", "BTC-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_tdv2(self):
        self.strategy = TDSeqStrategy()

        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "0.5")
        self.bus = EventBus()

        workflow = ViewWorkflow(self.strategy, "5m", "2024-09-25", "2024-10-04", "ULTI-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['countdown'], mode='lines', name='tdc'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=[13] * len(df), mode='lines', name='sell'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=[-13] * len(df), mode='lines', name='buy'), row=2, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['atr'], mode='lines', name='atr'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['atrma'], mode='lines', name='atrma'), row=3, col=1)

        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_tdv2_c(self):
        workflow = SymbolChooseWorkflow(TDSeqStrategy,
                                        {
                                            "direction": 4,
                                            "max_single_position": "0.5",
                                            "total_amount": 10000
                                        }
        , "15m", "2024-07-19 23:30", "2024-10-21 23:30")
        workflow.start(sort_func=draw_fig(f"tdv2"))

if __name__ == '__main__':
    unittest.main()
