#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/7 22:40
# @Author  : shenglin.li
# @File    : strategy_rsrs_test.py
# @Software: PyCharm
import decimal
import unittest

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_rsrs import RSRSStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.trade.trade import PositionSide


class TestRSRS(unittest.TestCase):
    def test_handle(self):
        self.strategy = RSRSStrategy(18, 120)

        PositionDirectionManager.__init__(self.strategy, PositionSide.FLAT)
        PositionRateManager.__init__(self.strategy, "1")
        DynamicRiskControl.__init__(self.strategy, 14, "100.3", "110.02")
        self.bus = EventBus()

        # workflow = ViewWorkflow(self.strategy, "1d", "2002-01-15", "2024-05-28", "000300", 1)
        workflow = ViewWorkflow(self.strategy, "4h", "2021-01-01", "2024-05-28", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df["benchmark"] = df["close"] / df.iloc[1]["close"]
        df["profit"] = df["balance"] / decimal.Decimal("1000")
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['beta'], mode='lines', name='beta'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        # 计算均值
        mean_beta = df['beta'].mean()

        # 计算标准差
        std_beta = df['beta'].std()

        print(f"Mean of 'beta': {mean_beta}")
        print(f"Standard deviation of 'beta': {std_beta}")
        # # 计算df["beta"]的均值和标准差
        # mean_beta = df["beta"].mean()
        # std_beta = df["beta"].std()
        #
        # # 为了拟合beta分布，我们通常需要两个参数alpha和beta
        # # 这里我们使用均值和标准差来估计alpha和beta，这只是一个简化的方法
        # alpha = mean_beta ** 2 * (std_beta ** 2 - mean_beta) / (
        #             std_beta ** 2 * (mean_beta - std_beta) ** 2 + mean_beta ** 2)
        # beta_param = alpha * (mean_beta - std_beta ** 2) / mean_beta ** 2
        #
        # # 创建一个包含x值的数组，用于计算拟合的beta分布的PDF
        # x = np.linspace(df["beta"].min(), df["beta"].max(), 100)
        # from scipy.stats import beta
        # # 计算PDF
        # pdf = beta.pdf(x, alpha, beta_param)
        #
        # # 创建直方图的trace
        # hist_trace = go.Histogram(
        #     x=df["beta"],
        #     histnorm='probability',
        #     name='Histogram of Beta'
        # )
        #
        # # 创建PDF的trace
        # pdf_trace = go.Scatter(
        #     x=x,
        #     y=pdf,
        #     mode='lines',
        #     name='Fitted Beta PDF'
        # )
        #
        # # 创建图表布局
        # layout = go.Layout(
        #     title='Beta Distribution Fit to DataFrame Column',
        #     xaxis=dict(title='Beta Value'),
        #     yaxis=dict(title='Density'),
        #     legend=dict(orientation="h"),
        # )
        #
        # # 创建图表对象
        # fig = go.Figure(data=[hist_trace, pdf_trace], layout=layout)
        #
        # # 显示图表
        # fig.show()
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.show()


if __name__ == '__main__':
    unittest.main()
