#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/14 20:10
# @Author  : shenglin.li
# @File    : dk_test.py
# @Software: PyCharm
import unittest

import pandas as pd

from leek.runner.view import ViewWorkflow
from leek.t import DK, MA, SuperSmoother, UltimateOscillator, HMA
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.t import LLT, KAMA, FRAMA, WMA


class TestKDJ(unittest.TestCase):
    def test_handle(self):
        workflow = ViewWorkflow(None, "1d", "2023-12-01", "2024-06-14", "002459", 1)
        # workflow = ViewWorkflow(self.strategy, "15m", "2024-03-15", "2024-05-24", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "4h", "2024-03-15", "2024-05-24", "BTC-USDT-SWAP")
        data = workflow.get_data("603005")
        dk = FRAMA(5)
        dk1 = FRAMA(30)
        dk2 = FRAMA(60)
        for d in data:
            d.ma5 = dk.update(d)
            d.ma10 = dk1.update(d)
            d.ma20 = dk2.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma5'], mode='lines', name='MA5', line=dict(color='black', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma10'], mode='lines', name='MA30', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma20'], mode='lines', name='MA60', line=dict(color='green', width=1)), row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_super(self):
        workflow = ViewWorkflow(None, "15m", "2024-10-07 14:30", "2024-10-10 18:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        p = 10
        p1 = 20
        ss = SuperSmoother(p)
        ss1 = SuperSmoother(p1)
        ma = MA(p)
        ma1 = MA(p1)
        # uo = UltimateOscillator(p)
        for d in data:
            d.ss1 = ss.update(d)
            d.ss2 = ss1.update(d)
            # d.uo = uo.update(d)
            d.ma1 = ma.update(d)
            d.ma2 = ma1.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ss1'], mode='lines', name='ss5', line=dict(color='black', width=1)),row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ss2'], mode='lines', name='ss20', line=dict(color='black', width=2)),row=1, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['uo'], mode='lines', name='uo', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma1'], mode='lines', name='ma5', line=dict(color='green', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma2'], mode='lines', name='ma20', line=dict(color='green', width=2)), row=1, col=1)
        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_wma(self):
        workflow = ViewWorkflow(None, "15m", "2024-10-07 14:30", "2024-10-10 18:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        ss = HMA(7)
        ss1 = HMA(50)
        for d in data:
            d.ss1 = ss.update(d)
            d.ss2 = ss1.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ss1'], mode='lines', name='ss1', line=dict(color='orange', width=1)),row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ss2'], mode='lines', name='ss2', line=dict(color='black', width=1)),row=1, col=1)
        workflow.draw(fig=fig, df=df)
        fig.show()

if __name__ == '__main__':
    unittest.main()
