#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/17 22:40
# @Author  : shenglin.li
# @File    : strategy_sar_test.py
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
from leek.strategy.strategy_htm import HTMStrategy
from leek.strategy.strategy_sar import SARStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.t.sar import SAR
from leek.trade.trade import PositionSide


class TestTD(unittest.TestCase):
    def test_handle(self):
        self.strategy = HTMStrategy()
        workflow = ViewWorkflow(self.strategy, "15m", "2024-01-27 14:15", "2024-05-28 16:30", "THETA-USDT-SWAP")
        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        JustFinishKData.__init__(self.strategy, False)
        DynamicRiskControl.__init__(self.strategy, 14, "1.3", "0.02")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma'], mode='lines', name='MA'), row=1, col=1)
        print(len(df))
        fig.show()
        # import matplotlib
        # matplotlib.use('TkAgg')
        # import matplotlib.pyplot as plt
        # plt.plot(df["r"], df["i"])
        # plt.title('Simple Line Chart')  # 添加标题
        # plt.xlabel('X Axis')  # X轴标签
        # plt.ylabel('Y Axis')  # Y轴标签
        # plt.show()  # 显示图表


if __name__ == '__main__':
    unittest.main()
