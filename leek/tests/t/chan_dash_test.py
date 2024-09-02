#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/29 19:22
# @Author  : shenglin.li
# @File    : chan_dash_test.py
# @Software: PyCharm
import unittest

from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from leek.t.chan.bi import ChanBIManager
from leek.t.chan.enums import BiFXValidMethod
from leek.t.chan.k import *
from leek.t.chan.seg import ChanSegmentManager
from leek.t.chan.zs import ChanZSManager

# 创建 Dash 应用
app = dash.Dash(__name__)

# 创建应用布局
app.layout = html.Div([
    dcc.Graph(id='candlestick-chart'),
    dcc.Interval(
        id='interval-component',
        interval=50,
        n_intervals=0
    )
])
data_g = []
data_list = []

# 回调函数更新图表
@app.callback(
    Output('candlestick-chart', 'figure'),
    Output('interval-component', 'interval'),
    Input('interval-component', 'n_intervals'),
    State('interval-component', 'interval')
)
def update_graph(n, interval):
    if n >= len(data_g):
        return None, 50000
    return chan_calc(n), interval


def draw_data():
    df = pd.DataFrame([x.__json__() for x in data_list])
    df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True)

    fig.add_trace(go.Candlestick(x=df['Datetime'],
                       open=df['open'],
                       high=df['high'],
                       low=df['low'],
                       close=df['close'],
                       name=df.iloc[0]["symbol"]))

    if "bi" in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                       name='chan b', connectgaps=True), row=1, col=1)
    if "bi_" in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                       name='chan b', connectgaps=True), row=1, col=1)
    if "seg" in df.columns:
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                 name='segment', connectgaps=True), row=1, col=1)
    if "seg_" in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                       name='segment', connectgaps=True), row=1, col=1)
    # zs
    colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
    for level in zs_manager.zs_dict:
        for zs in zs_manager.zs_dict[level]:
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[level - 1], width=zs.level),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
    if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy:
        zs = zs_manager.cur_zs
        fig.add_shape(
            type='rect',
            x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
            x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
            line=dict(color=colors[zs.level - 1], width=zs.level, dash='dash'),
            fillcolor=None,  # 透明填充，只显示边框
            name='Highlight Area'
        )
    fig.update_layout(
        title='K',
        xaxis_title='time',
        yaxis_title='price',
        xaxis_rangeslider_visible=False
    )

    return fig

bi_manager = ChanBIManager(bi_valid_method=BiFXValidMethod.STRICT)
seg_manager = ChanSegmentManager()
zs_manager = ChanZSManager(max_level=2)
def chan_calc(n):
    global data_list
    if n == 0:
        data_list = []
    # chan_k = k_mgr.update(d)
    d = data_g[n]
    bi_manager.update(d)
    # for bi in bi_manager:
    #     for ck in bi.chan_k_list:
    for k in data_list:
        k.bi = None
        k.bi_ = None
        k.seg = None
        k.seg_ = None
    if not bi_manager.is_empty():
        seg_manager.update(bi_manager[-1])
        zs_manager.update(bi_manager[-1])

    for bi in bi_manager:
        bi.mark_on_data()
    for seg in seg_manager:
        seg.mark_on_data()
    # chan_k.mark_on_data()
    if len(data_list) == 0 or data_list[-1].timestamp != d.timestamp:
        data_list.append(d)
    else:
        data_list[-1] = d
    return draw_data()


if __name__ == '__main__':
    # workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
    workflow = ViewWorkflow(None, "30m", "2024-07-17 08:20", "2024-08-30 20:30", "ETH-USDT-SWAP")
    data_g = workflow.get_data("ETH-USDT-SWAP")
    print("K线数量: ", len(data_g), len([d for d in data_g if d.finish == 1]))

    app.run_server(debug=True)
