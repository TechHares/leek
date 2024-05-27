#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/27 16:00
# @Author  : shenglin.li
# @File    : strategy_boll_test.py
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
from leek.strategy.strategy_bollinger_bands import BollingerBandsV2Strategy
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.trade.trade import PositionSide


class TestBoll(unittest.TestCase):
    def test_handle(self):
        self.strategy = BollingerBandsV2Strategy(window=20, num_std_dev="2.0", fast_period="9", slow_period="26",
                                                 smoothing_period="4")
        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        JustFinishKData.__init__(self.strategy, "False")
        DynamicRiskControl.__init__(self.strategy, 13, "1.3", "0.02")
        self.bus = EventBus()

        workflow = ViewWorkflow(self.strategy, "5m", "2024-03-15", "2024-05-28", "FIL-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['boll_upper_band'], mode='lines', name='up'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['boll_lower_band'], mode='lines', name='down'), row=1, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()

