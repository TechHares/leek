#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/14 20:10
# @Author  : shenglin.li
# @File    : dk_test.py
# @Software: PyCharm
import unittest

import pandas as pd

from leek.runner.view import ViewWorkflow
from leek.t import DK
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.t import LLT, KAMA, FRAMA


class TestKDJ(unittest.TestCase):
    def test_handle(self):
        # workflow = ViewWorkflow(None, "1d", "2023-12-01", "2024-06-14", "002459", 1)
        workflow = ViewWorkflow(None, "4h", "2024-03-15", "2024-05-24", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        dk = DK(LLT)
        for d in data:
            d.dk = dk.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dk'].apply(lambda x : 1 if x else 0), mode='lines', name='dk'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
