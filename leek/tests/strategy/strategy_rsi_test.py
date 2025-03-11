#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/7 22:40
# @Author  : shenglin.li
# @File    : strategy_rsi_test.py
# @Software: PyCharm
import decimal
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager, PositionSideManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_rsi import RSIStrategy, RSIV2Strategy
from leek.strategy.strategy_td import TDStrategy
from leek.trade.trade import PositionSide


class TestRSI(unittest.TestCase):
    def test_handle(self):
        self.strategy = RSIStrategy(period=5, over_buy=85, over_sell=15)
        self.strategy.rsi_func = [self.strategy.classic_rsi, self.strategy.ibs_rsi, self.strategy.mom_rsi]
        # self.strategy.rsi_func = [self.strategy.mom_rsi]

        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        JustFinishKData.__init__(self.strategy, "False")
        DynamicRiskControl.__init__(self.strategy, 14, "1.3", "0.02")
        self.bus = EventBus()

        workflow = ViewWorkflow(self.strategy, "1d", "2004-01-15", "2024-05-28", "000300", 1)
        # workflow = ViewWorkflow(self.strategy, "15m", "2024-03-15", "2024-05-24", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['rsi'], mode='lines', name='rsi'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_handle1(self):
        self.strategy = RSIV2Strategy(min_price="0.42", max_price="0.48", risk_rate="0.02",force_risk_rate="0.05",bias_risk_rate="3",
                                      position_split="1,2,3,4,5",
                                      start_condition="k.close < 0.45",
                                      stop_condition="k.close > 0.482",
                                      over_buy=80, over_sell=20)
        PositionSideManager.__init__(self.strategy, PositionSide.LONG)
        PositionRateManager.__init__(self.strategy, "0.3")
        self.bus = EventBus()

        workflow = ViewWorkflow(self.strategy, "5m", "2025-02-26", "2025-03-11", "CRV-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['rsi'], mode='lines', name='rsi'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

if __name__ == '__main__':
    unittest.main()
