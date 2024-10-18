#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/17 20:14
# @Author  : shenglin.li
# @File    : dsp_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.view import ViewWorkflow
from leek.t import SuperSmoother, MA, Reflex, TrendFlex


class TestKDJ(unittest.TestCase):
    def test_relex(self):
        workflow = ViewWorkflow(None, "15m", "2024-10-07 14:30", "2024-10-15 18:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        p = 10
        ss = SuperSmoother(p)
        ma = MA(p)
        reflex = Reflex(p)
        trend_flex = TrendFlex(p)
        for d in data:
            d.ss = ss.update(d)
            d.relex = reflex.update(d)
            d.trend_flex = trend_flex.update(d)
            d.ma = ma.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ss'], mode='lines', name='ss5', line=dict(color='black', width=1)),row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma'], mode='lines', name='ma5', line=dict(color='green', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['relex'], mode='lines', name='relex', line=dict(color='black', width=1)), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['relex'].ewm(span=3).mean(), mode='lines', name='relex3', line=dict(color='orange', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['trend_flex'], mode='lines', name='trend_flex', line=dict(color='black', width=1)), row=3, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['trend_flex'].ewm(span=3).mean(), mode='lines', name='trend_flex3', line=dict(color='orange', width=1)), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.show()

if __name__ == '__main__':
    unittest.main()
