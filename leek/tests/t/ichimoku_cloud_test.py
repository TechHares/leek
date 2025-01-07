#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/19 21:07
# @Author  : shenglin.li
# @File    : ichimoku_cloud_test.py
# @Software: PyCharm
import unittest
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow

from leek.t import ATR, RSI, DMI, IchimokuCloud


class TestICK(unittest.TestCase):
    def test_handle1(self):
        workflow = ViewWorkflow(None, "4h", "2024-10-20", "2024-12-12", "ETH-USDT-SWAP")
        v1 = IchimokuCloud()
        data = workflow.get_data("ETH-USDT-SWAP")
        for d in data:
            d.tenkan, d.base, d.span_a, d.span_b = v1.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['tenkan'], mode='lines', line=dict(color='green',width=1), name='转换线'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['base'], mode='lines', line=dict(color='red', width=1), name='基准线'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['span_a'], mode='lines', line=dict(color='blue', width=1), name='顶'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['span_b'], mode='lines', line=dict(color='gray', width=1), name='底'), row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()
if __name__ == '__main__':
    pass
