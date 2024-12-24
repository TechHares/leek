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
from leek.t import WR, RSI


class TestRSI(unittest.TestCase):
    def test_handle1(self):
        workflow = ViewWorkflow(None, "1m", "2024-06-18 14:30", "2024-06-18 18:30", "MERL-USDT-SWAP")
        v1 = WR(14)
        data = workflow.get_data("MERL-USDT-SWAP")
        for d in data:
            d.v1 = v1.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['v1'], mode='lines', name='rsi'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
