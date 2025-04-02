#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/10 22:40
# @Author  : shenglin.li
# @File    : strategy_turtle_test.py
# @Software: PyCharm
import unittest
from decimal import Decimal

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t import StochRSI, MACD, MERGE, Divergence


class TestMACD(unittest.TestCase):
    def test_handle(self):
        workflow = ViewWorkflow(None, "15m", "2024-10-07 14:30", "2024-10-10 18:30", "ULTI-USDT-SWAP")
        macd = MACD()
        data = workflow.get_data("ULTI-USDT-SWAP")
        for d in data:
            r = macd.update(d)
            if r:
                d.dif = r[0]
                d.dea = r[1]
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        df['his'] = df['dif'] - df['dea']
        df['color'] = np.where(df['his'] > 0, 'green', 'red')
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif', line={"color": "black", "width": 1}), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea', line={"color": "orange", "width": 1}), row=2, col=1)
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['his'], marker={"color": df['color']}, name='His'), row=2, col=1)
        # fig.add_trace(go.Bar(x=df['Datetime'], y=(df['dif'] - df['dea']).clip(lower=0), marker={"color": "green"}, name='His'), row=2, col=1)
        # fig.add_trace(go.Bar(x=df['Datetime'], y=(df['dif'] - df['dea']).clip(upper=0), marker={"color": "red"}, name='His'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        fig.update_layout(
            barmode='relative'
        )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        print(len(df))
        fig.show()

    def test_merge(self):
        workflow = ViewWorkflow(None, "15m", "2024-10-07 14:30", "2024-10-10 18:30", "ULTI-USDT-SWAP")
        m = MERGE(3)
        data = workflow.get_data("ULTI-USDT-SWAP")
        rs = []
        for d in data:
            r = m.update(d)
            if r.finish == 1:
                rs.append(r)
        print(len(data), len(data)//3, len(rs))

    def test_divergence(self):
        workflow = ViewWorkflow(None, "30m", "2025-02-25 14:30", "2025-03-17 18:30", "CRV-USDT-SWAP")
        macd = MACD(12, 26, 9)
        divergence = Divergence(divergence_threshold=2, pull_back_rate=0.3, dea_pull_back=False)
        data = workflow.get_data(workflow.benchmark)
        lst = []
        idx = 0
        for d in data:
            idx += 1
            d.idx = "%s" % idx
            r = macd.update(d)
            d.x = 0
            if r:
                d.dif = r[0]
                d.dea = r[1]
                if d.dif is None or d.dea is None:
                    continue
                d.m = r[0] - r[1]
                lst.append(d)
                if divergence.is_top_divergence(lst):
                    d.x = 1
                if divergence.is_bottom_divergence(lst):
                    d.x = -1

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'], mode='lines', name='dif',
                                 line={"color": "black", "width": 1}), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'], mode='lines', name='dea',
                                 line={"color": "orange", "width": 1}), row=2, col=1)
        df['color'] = np.where(df['m'] > 0, 'green', 'red')
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['m'], marker={"color": df['color']}, name='His'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['x'], name='His', mode='lines'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        fig.update_layout(
            barmode='relative'
        )
        fig.add_trace(go.Scatter(
            x=df['Datetime'],
            y=df['high'] * Decimal("1.05"),
            mode='markers+text',
            text=df["idx"],
            marker=dict(color='green', size=4)
        ), row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
