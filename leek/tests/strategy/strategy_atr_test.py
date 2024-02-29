#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/26 10:59
# @Author  : shenglin.li
# @File    : strategy_atr_test.py
# @Software: PyCharm
from decimal import Decimal

import pandas as pd
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
import plotly.graph_objs as go


# 计算随机指标
def calculate_stochastics(df, k_period=14, d_period=1, smooth=3):
    low_min = df['low'].rolling(window=k_period).min().apply(lambda x: Decimal(x))
    high_max = df['high'].rolling(window=k_period).max().apply(lambda x: Decimal(x))
    df['%K'] = (df['close'] - low_min) / (high_max - low_min) * 100
    df['%K_smooth'] = df['%K'].rolling(window=smooth).mean().apply(lambda x: Decimal(x))
    df['%D'] = df['%K_smooth'].rolling(window=d_period).mean().apply(lambda x: Decimal(x))
    return df


if __name__ == '__main__':
    from leek.strategy.common import SymbolsFilter, PositionDirectionManager, CalculatorContainer, AtrStopLoss
    from leek.strategy.strategy_atr_ha import ATRHeikinAshiStrategy

    strategy = ATRHeikinAshiStrategy()
    SymbolsFilter.__init__(strategy)
    CalculatorContainer.__init__(strategy, 30)
    PositionDirectionManager.__init__(strategy)
    AtrStopLoss.__init__(strategy)
    # workflow = ViewWorkflow(strategy, "15m", 1703132100000, 1703337300000, "ETHUSDT")
    workflow = ViewWorkflow(strategy, "15m", 1647532800000, 1649174400000, "ETHUSDT")
    # workflow = ViewWorkflow(strategy, "15m", 1647532800000, 1647626400000, "ETHUSDT")

    workflow.start()
    df = pd.DataFrame(workflow.kline_data)
    df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
    fig = workflow.draw(fig=fig, df=df)

    # 计算 ATR
    df['TR'] = df['high'] - df['low']
    df['TR1'] = abs(df['high'] - df['close'].shift(1))
    df['TR2'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['TR', 'TR1', 'TR2']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()

    # 计算 Heikin-Ashi
    df["ha_close"] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df["ha_open"] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    df["ha_high"] = df[['high', 'open', 'close']].max(axis=1)
    df["ha_low"] = df[['low', 'open', 'close']].min(axis=1)

    # 添加 Heikin-Ashi
    fig.add_trace(go.Candlestick(x=df['Datetime'],
                                 open=df['ha_open'],
                                 high=df['ha_high'],
                                 low=df['ha_low'],
                                 close=df['ha_close'],
                                 name='Heikin-Ashi'), row=4, col=1)
    df = calculate_stochastics(df)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['%K'], mode='lines', name='%K', line=dict(color='red')), row=3,
                  col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['%D'], mode='lines', name='%D', line=dict(color='blue')), row=3,
                  col=1)

    # 添加 ATR 指标
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ATR'],
                             mode='lines', name='ATR', line=dict(color='orange', width=1)),
                  row=2, col=1)
    # 禁用第一行的滑动条
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
    fig.show()
