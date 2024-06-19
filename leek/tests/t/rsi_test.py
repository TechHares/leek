#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/18 22:40
# @Author  : shenglin.li
# @File    : strategy_turtle_test.py
# @Software: PyCharm
import unittest

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t import StochRSI, RSI


class TestRSI(unittest.TestCase):
    def test_handle1(self):
        workflow = ViewWorkflow(None, "1m", "2024-06-18 14:30", "2024-06-18 18:30", "MERL-USDT-SWAP")
        kdj = RSI()
        data = workflow.get_data("MERL-USDT-SWAP")
        for d in data:
            d.rsi = kdj.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['rsi'], mode='lines', name='rsi'), row=2, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_handle2(self):
            workflow = ViewWorkflow(None, "1m", "2024-06-18 14:30", "2024-06-18 18:30", "MERL-USDT-SWAP")
            kdj = StochRSI(14, 14, 3, 3)
            data = workflow.get_data("MERL-USDT-SWAP")
            for d in data:
                r = kdj.update(d)
                if r:
                    d.k, d.d = r
            df = pd.DataFrame([x.__json__() for x in data])
            df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['stoch_rsi'], mode='lines',
            #                          line=dict(color='black', width=1), name='rsi'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines',
                                     line=dict(color='black', width=1), name='k'), row=2, col=1)
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines',
            #                          line=dict(color='orange', width=1), name=''), row=2, col=1)

            # import talib
            # rsi = talib.STOCHRSI(df['close'], 14, 14, 3, 3)
            #
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=rsi[0], mode='lines',
            #                          line=dict(color='black', width=1), name='rsi'), row=3, col=1)
            # fig.add_trace(go.Scatter(x=df['Datetime'], y=rsi[1], mode='lines',
            #                          line=dict(color='orange', width=1), name='k'), row=3, col=1)

            fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
            fig.update_xaxes(rangeslider_visible=True, row=3, col=1)
            workflow.draw(fig=fig, df=df)
            print(len(df))
            # print("TALIB:", rsi[0].fillna(0).tolist())
            print("WE___:", df['k'].fillna(0).tolist())
            fig.show()


if __name__ == '__main__':
    unittest.main()
