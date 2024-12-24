#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/18 22:40
# @Author  : shenglin.li
# @File    : atr_test.py
# @Software: PyCharm
import unittest

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t import ATR, RSI, DMI


class TestDM(unittest.TestCase):
    def test_handle1(self):
        workflow = ViewWorkflow(None, "4h", "2024-11-20", "2024-12-12", "ETH-USDT-SWAP")
        v1 = DMI()
        data = workflow.get_data("ETH-USDT-SWAP")
        for d in data:
            d.adx, d.up, d.down = v1.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['adx'], mode='lines', name='adx'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['up'], mode='lines', line=dict(
            color='green',
            width=1
        ), name='DI+'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['down'], mode='lines', line=dict(
            color='red',
            width=1
        ), name='DI-'), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
