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
    from leek.strategy.strategy_mean import SingleMaStrategy

    strategy = SingleMaStrategy()
    PositionRateManager.__init__(strategy, 0.5)
    CalculatorContainer.__init__(strategy, 19)
    workflow = ViewWorkflow(strategy, "5m", 1710000000000, 1710259200000, "ZRXUSDT")
    workflow.start()
    df = pd.DataFrame(workflow.kline_data)
    df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig = workflow.draw(fig=fig, df=df, row=1)
    workflow.draw(fig=fig, df=df)

    df['change_value'] = (df["close"] - df["close"].shift(strategy.window)).abs()
    df['volatility_value'] = df["close"].diff(strategy.window).abs().sum()
    df['er'] = (df['change_value'] / df['volatility_value'])
    fast_sc = Decimal(2 / (2 + 1))
    slow_sc = Decimal(2 / (30 + 1))

    df['ssc'] = (df['er'] * (fast_sc - slow_sc) + slow_sc) * 2
    # 初始化AMA
    df['ama'] = df['close'].copy()
    # df['ama'] = df['ama'].shift(1) + df['ssc'] * (df['close'] - df['ama'].shift(1))
    # 更新AMA
    for i in range(strategy.window, len(df)):
        df.loc[i, 'ama'] = df.loc[i - 1, 'ama'] + (df.loc[i, 'ssc'] * (df.loc[i, 'close'] - df.loc[i - 1, 'ama']))
    df['ma'] = df['ama']
    df['ma_fast'] = df['close'].rolling(window=strategy.window).mean().apply(lambda x: Decimal(x))
    # 添加 ma 指标
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma'],
                             mode='lines', name='ma', line=dict(color='orange', width=1)), row=1, col=1)
    # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_fast'],
    #                          mode='lines', name='ma_fast', line=dict(color='red', width=1)), row=1, col=1)
    fig.show()
