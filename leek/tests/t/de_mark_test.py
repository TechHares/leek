#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/21 19:29
# @Author  : shenglin.li
# @File    : de_mark_test.py
# @Software: PyCharm
import unittest

import pandas as pd
from plotly.subplots import make_subplots

from leek.common import KlineLevel
from leek.common.utils import DateTime
from leek.runner.view import ViewWorkflow
from leek.t import DeMarker, TDSequence, StochRSI, TDTrendLine
import plotly.graph_objs as go


class TestDeMark(unittest.TestCase):
    def test_DeMarker(self):
        workflow = ViewWorkflow(None, "30m", "2024-10-09", "2024-10-24", "ULTI-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        dmk = DeMarker(10)
        for d in data:
            d.dmk = dmk.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dmk'], mode='lines', name='DMK'), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_td_seq(self):
        workflow = ViewWorkflow(None, "30m", "2024-07-09", "2024-10-24", "CRV-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        tds = TDSequence(perfect_countdown=True)
        stoch_rsi = StochRSI()
        for d in data:
            d.tdc = tds.update(d).countdown
            d.k, d.d = stoch_rsi.update(d)
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        df['sell'] = 13
        df['buy'] = -13
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['tdc'], mode='lines', name='tdc'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['sell'], mode='lines', name='sell'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['buy'], mode='lines', name='buy'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', name='k'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines', name='d'), row=3, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_td_trend(self):
        workflow = ViewWorkflow(None, "4h", "2024-12-01", "2024-12-24", "ETH-USDT-SWAP")
        data = workflow.get_data(workflow.benchmark)
        tdl = TDTrendLine(n = 3, atr_mult=10, just_confirm=True)
        for d in data:
            v = tdl.update(d)
            if v:
                d.up_line = v[0]
                d.down_line = v[1]
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['up_line'], mode='lines',text="U", name='up line'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['down_line'], mode='lines',text="D", name='down line'), row=1, col=1)
        colors = [
            "blue",  # 蓝色
            "orange",  # 橙色
            "green",  # 绿色
            "red",  # 红色
            "purple",  # 紫色
            "brown",  # 棕色
            "pink",  # 粉红色
            "gray",  # 灰色
            "yellowgreen",  # 黄绿色
            "cyan",  # 青色
            "indigo",  # 靛蓝色
            "gold",  # 金色
            "lime",  # 酸橙绿
            "magenta",  # 品红色
            "yellow",  # 黄色
            "teal",  # 青绿色
            "fuchsia",  # 紫红色
            "olive",  # 橄榄绿
            "maroon",  # 栗色
            "aqua"  # 浅绿色
        ]
        idx = 0
        for line in tdl.lines:
            color = colors[idx % len(colors)]
            idx += 1
            if line[0].end == 0:
                continue
            t = line[0].start
            up_time = []
            up_idx = 0
            up_value = []
            while t <= line[0].end:
                up_time.append(DateTime.to_datetime(t + 8 * 60 * 60 * 1000))
                up_value.append(line[0].call_value(line[0].p1.idx + up_idx))
                up_idx += 1
                t += KlineLevel.H4.milliseconds

            t = line[1].start
            down_time = []
            down_idx = 0
            down_value = []
            while t <= line[1].end:
                down_time.append(DateTime.to_datetime(t + 8 * 60 * 60 * 1000))
                down_value.append(line[1].call_value(line[1].p1.idx + down_idx))
                down_idx += 1
                t += KlineLevel.H4.milliseconds

            # fig.add_trace(go.Scatter(x=up_time, y=up_value, mode='lines', line=dict(color=color, width=1), name='UP LINE'), row=1, col=1)
            # fig.add_trace(go.Scatter(x=down_time, y=down_value, mode='lines', line=dict(color=color, width=1), name='DOWN LINE'), row=1, col=1)

        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['up'], mode='markers',text="H", name='up'), row=1, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['down'], mode='markers',text="L", name='down'), row=1, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()


if __name__ == '__main__':
    unittest.main()
