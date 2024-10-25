#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/21 19:29
# @Author  : shenglin.li
# @File    : de_mark_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t import DeMarker, TDSequence, StochRSI
import plotly.graph_objs as go


class TestDeMark(unittest.TestCase):
    def test_DeMarker(self):
        workflow = ViewWorkflow(None, "30m", "2024-10-09", "2024-10-24", "ULTI-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        dmk = DeMarker(10)
        for d in data:
            d.dmk = dmk.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dmk'], mode='lines', name='DMK'), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_td_seq(self):
        workflow = ViewWorkflow(None, "30m", "2024-07-09", "2024-10-24", "CRV-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        tds = TDSequence(perfect_countdown=True)
        stoch_rsi = StochRSI()
        for d in data:
            d.tdc = tds.update(d).countdown
            d.k, d.d = stoch_rsi.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df['sell'] = 13
        df['buy'] = -13
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['tdc'], mode='lines', name='tdc'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['sell'], mode='lines', name='sell'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['buy'], mode='lines', name='buy'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', name='k'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines', name='d'), row=3, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
