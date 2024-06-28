#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/27 20:35
# @Author  : shenglin.li
# @File    : strategy_dk_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.view import ViewWorkflow
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.strategy.strategy_dk import DKStrategy


class TestTD(unittest.TestCase):
    def test_handle(self):
        self.strategy = DKStrategy()
        workflow = ViewWorkflow(self.strategy, "4h", "2021-03-27 14:15", "2024-06-28 16:30", "BTC-USDT-SWAP")
        PositionRateManager.__init__(self.strategy, "1")
        DynamicRiskControl.__init__(self.strategy, 14, "1.3", "0.02")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dk'], mode='lines', name='DK'), row=2, col=1)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
