#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/8 22:40
# @Author  : shenglin.li
# @File    : strategy_chan_test.py
# @Software: PyCharm
import decimal
import unittest
from decimal import Decimal

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl, StopLoss
from leek.strategy.strategy_chan import ChanStrategy
from leek.strategy.strategy_chan1 import ChanV2Strategy
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.trade.trade import PositionSide


class TestChan1(unittest.TestCase):
    def test_handle(self):
        self.strategy = ChanV2Strategy(allow_similar_zs=False, divergence_rate=0.98)
        PositionRateManager.__init__(self.strategy, 1)
        StopLoss.__init__(self.strategy, Decimal("0.1"))
        PositionDirectionManager.__init__(self.strategy, 4)
        JustFinishKData.__init__(self.strategy, False)

        self.bus = EventBus()
        # workflow = ViewWorkflow(self.strategy, "1m", "2025-03-01 23:10", "2025-03-25 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "1m", "2025-03-01 00:00", "2025-04-08 00:00", "CRV-USDT-SWAP")
        workflow = ViewWorkflow(self.strategy, "1m", "2025-03-01 00:00", "2025-03-05 00:00", "CRV-USDT-SWAP")

        workflow.start()

        self.strategy.chan.mark_on_data()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        print(df.columns)
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        if "current_ps" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df["current_ps"], mode='text', text=df["current_pst"],
                                     name='current_ps'),
                          row=1, col=1)
        if "seg" in df.columns:
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=df["seg_value"], mode='text', text=df["seg_idx"], name='seg_idx'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                           name='segment', connectgaps=True), row=1, col=1)

        if "lower_ps" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df["lower_ps"], mode='text', text=df["lower_pst"], name='lower_pst'),row=1, col=1)
        if "bi" in df.columns:
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='bi_idx'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                     name='chan b', connectgaps=True), row=1, col=1)

        if "bi_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                           name='chan b', connectgaps=True), row=1, col=1)

        # if "dr" in df.columns:
        #     fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dr'], mode='lines', line=dict(color='darkblue', width=3),
        #                              name='chan dr', connectgaps=True), row=1, col=1)
        # if "dr_" in df.columns:
        #     fig.add_trace(
        #         go.Scatter(x=df['Datetime'], y=df['dr_'], mode='lines',
        #                    line=dict(color='darkblue', width=3, dash='dash'),
        #                    name='chan dr', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif',
                                 line={"color": "black", "width": 1}), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea',
                                 line={"color": "orange", "width": 1}), row=2, col=1)
        df['color'] = np.where(df['m'] > 0, 'green', 'red')
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['m'], marker={"color": df['color']}, name='His'), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_layout(height=650)
        workflow.draw(fig=fig, df=df)
        fig.show()


if __name__ == '__main__':
    unittest.main()
