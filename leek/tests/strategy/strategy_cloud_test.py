#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/30 20:35
# @Author  : shenglin.li
# @File    : strategy_dmi_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData, FallbackTakeProfit
from leek.strategy.strategy_dmi import DMIStrategy
from leek.strategy.strategy_ichimoku_cloud import IchimokuCloudStrategy
from leek.tests.strategy.symbol_choose_test import draw_fig


class TestTD(unittest.TestCase):
    def test_handle(self):
        self.strategy = IchimokuCloudStrategy()
        workflow = ViewWorkflow(self.strategy, "5m", "2024-10-21 00:00", "2024-12-25 19:30", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "5m", "2024-12-01 00:00", "2024-12-20 10:30", "CRV-USDT-SWAP")
        PositionDirectionManager.__init__(self.strategy, 1)
        PositionRateManager.__init__(self.strategy, 1)
        DynamicRiskControl.__init__(self.strategy, window=14, atr_coefficient="3", stop_loss_rate="0.02")
        JustFinishKData.__init__(self.strategy, True)
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        # kline.adx, kline.up_di, kline.down_di, kline.rsi_k, kline.rsi_d = adx, up_di, down_di, k, d
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['adx'], mode='lines', name='adx'), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['adxr'], mode='lines', name='adxr'), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=[25] * len(df["Datetime"]), mode='lines', name='adx_threshold'), row=2, col=1)

        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['up_di'], mode='lines', line=dict(color='green', width=1), name='DI+'), row=3, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['down_di'], mode='lines', line=dict(color='red', width=1), name='DI-'), row=3, col=1)

        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['rsi_k'], mode='lines', name='rsi_k'), row=4, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['rsi_d'], mode='lines', name='rsi_d'), row=4, col=1)

        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.show()

    def test_choose(self):
        workflow = SymbolChooseWorkflow(IchimokuCloudStrategy, {
            "max_single_position": "1",
            "total_amount": "1000",
            "just_finish_k": True,
            "direction": "4",

        }, "5m", "2024-12-21 00:00", "2024-12-25 19:30")
        workflow.start(sort_func=draw_fig(f"ICO"))


if __name__ == '__main__':
    unittest.main()
