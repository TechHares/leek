#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/26 10:59
# @Author  : shenglin.li
# @File    : strategy_atr_test.py
# @Software: PyCharm
from decimal import Decimal

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
import plotly.graph_objs as go

from leek.strategy.common.strategy_common import PositionRateManager

if __name__ == '__main__':
    from leek.strategy.common import SymbolsFilter, PositionDirectionManager, CalculatorContainer, AtrStopLoss
    from leek.strategy.strategy_macd import MacdStrategy

    strategy = MacdStrategy(5, 17, 60, 7)
    PositionRateManager.__init__(strategy, 0.5)
    workflow = ViewWorkflow(strategy, "5m", 1710000000000, 1710259200000, "ZRXUSDT")
    workflow.start()
    df = pd.DataFrame(workflow.kline_data)
    df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig = workflow.draw(fig=fig, df=df, row=1)
    # workflow.draw(fig=fig, df=df)

    df['avg_price'] = df['amount'] / df['volume']
    df['ma_fast'] = df['avg_price'].rolling(window=strategy.fast_line_period).mean().apply(lambda x: Decimal(x))
    df['ma_slow'] = df['avg_price'].rolling(window=strategy.slow_line_period).mean().apply(lambda x: Decimal(x))
    df['ma_long'] = df['avg_price'].rolling(window=strategy.long_line_period).mean().apply(lambda x: Decimal(x))
    # df['ma_fast'] = df['close'].rolling(window=5).mean().apply(lambda x: Decimal(x))
    # df['ma_slow'] = df['close'].rolling(window=17).mean().apply(lambda x: Decimal(x))
    # df['ma_long'] = df['close'].rolling(window=60).mean().apply(lambda x: Decimal(x))

    df['dif'] = df['ma_fast'] - df['ma_slow']
    df['dea'] = df['dif'].ewm(span=strategy.average_moving_period, adjust=False).mean().apply(lambda x: Decimal(x))
    df['m'] = df['dif'] - df['dea']
    # 添加 ma 指标
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dif'],
                             mode='lines', name='dif', line=dict(color='black', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dea'],
                             mode='lines', name='dea', line=dict(color='orange', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['m'],
                             mode='lines', name='m', line=dict(color='green', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_fast'],
                             mode='lines', name='ma_fast', line=dict(color='black', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_slow'],
                             mode='lines', name='ma_slow', line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_long'],
                             mode='lines', name='ma_long', line=dict(color='red', width=1)), row=1, col=1)
    fig.show()
