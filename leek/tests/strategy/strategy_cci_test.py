#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/28 20:35
# @Author  : shenglin.li
# @File    : strategy_cci_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.view import ViewWorkflow
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.strategy.strategy_cci import CCIStrategy
from leek.strategy.strategy_dmi import DMIStrategy


class TestCCI(unittest.TestCase):
    def test_handle(self):
        self.strategy = CCIStrategy()
        # workflow = ViewWorkflow(self.strategy, "5m", "2024-12-21 00:00", "2024-12-25 19:30", "CRV-USDT-SWAP")
        workflow = ViewWorkflow(self.strategy, "5m", "2024-12-01 00:00", "2024-12-20 10:30", "CRV-USDT-SWAP")
        PositionRateManager.__init__(self.strategy, "1")
        PositionDirectionManager.__init__(self.strategy, 4)
        DynamicRiskControl.__init__(self.strategy, window=14, atr_coefficient="2.5", stop_loss_rate="0.02")
        JustFinishKData.__init__(self.strategy, True)
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['fast_ma'], mode='lines', name='fast_ma'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['slow_ma'], mode='lines', name='slow_ma'), row=1, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=[100] * len(df["Datetime"]), mode='lines', name='adx_threshold'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['cci'], mode='lines', line=dict(color='red', width=1), name='CCI'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=[-100] * len(df["Datetime"]), mode='lines', name='adx_threshold'), row=2, col=1)

        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.show()


if __name__ == '__main__':
    unittest.main()
