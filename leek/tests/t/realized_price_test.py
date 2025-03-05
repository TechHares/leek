#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/9 20:08
# @Author  : shenglin.li
# @File    : realized_price_test.py
# @Software: PyCharm
import unittest
from collections import OrderedDict

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow


class TestRPrice(unittest.TestCase):
    def test_handle(self):
        workflow = ViewWorkflow(None, "1m", "2025-01-01 00:00", "2025-01-10 18:30", "BTC-USDT-SWAP")
        data = workflow.get_data("BTC-USDT-SWAP")
        df = pd.DataFrame([x.__json__() for x in data])
        period = 10
        max_value = int(df['high'].max() + period)
        min_value = int(df['low'].min())
        max_value = max_value - max_value % period
        min_value = min_value - min_value % period
        print(min_value, max_value)
        r = OrderedDict()
        for i in range(min_value, max_value, period):
            r[i] = 0
        for d in data:
            price = d.amount * 100 / d.volume if d.volume > 0 else 0
            print(d.amount, d.volume, price, d.close)
            price = int(price - price % period)
            print(price)
            if price > 0:
                r[price] += float(d.volume)
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Bar(x=list(r.keys()), y=list(r.values()), name='His'), row=1, col=1)
        fig.update_layout(
            barmode='relative'
        )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        print(len(df))
        fig.show()
if __name__ == '__main__':
    pass
