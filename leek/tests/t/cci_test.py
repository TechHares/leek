#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/31 22:40
# @Author  : shenglin.li
# @File    : cci_test.py
# @Software: PyCharm
import unittest

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t import CCI, CCIV2


class TestCCI(unittest.TestCase):
    def test_handle1(self):
        workflow = ViewWorkflow(None, "15m", "2024-12-28", "2024-12-30", "CRV-USDT-SWAP")
        v1 = CCI()
        v2 = CCIV2()
        data = workflow.get_data("CRV-USDT-SWAP")
        for d in data:
            d.cci = v1.update(d)
            d.cci2 = v2.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['cci'], mode='lines', name='cci'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['cci2'], mode='lines', name='cci2'), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
