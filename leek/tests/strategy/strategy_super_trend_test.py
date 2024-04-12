#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/11 20:35
# @Author  : shenglin.li
# @File    : strategy_super_trend.py
# @Software: PyCharm
from decimal import Decimal

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.strategy_super_trend import SuperTrendStrategy

if __name__ == '__main__':
    strategy = SuperTrendStrategy(10, 3)
    PositionRateManager.__init__(strategy, "0.5")

    # workflow = ViewWorkflow(strategy, "5m", 1707840000000, 1708444800000, "ZRXUSDT")
    workflow = ViewWorkflow(strategy, "5m", 1710000000000, 1710604800000, "ZRXUSDT")
    workflow.start()

    df = pd.DataFrame(workflow.kline_data)
    df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig = workflow.draw(fig=fig, df=df, row=1)

    # 计算 ATR
    df['TR'] = df['high'] - df['low']
    df['TR1'] = abs(df['high'] - df['close'].shift(1))
    df['TR2'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['TR', 'TR1', 'TR2']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=strategy.period).mean().apply(lambda x: Decimal(x))

    # 根据价格位置确定超级趋势
    upper_band = df["close"] + (strategy.factory * df['ATR'])
    lower_band = df["close"] - (strategy.factory * df['ATR'])

    supertrend = df["close"].copy()
    trend = -1
    for i in range(1, len(df)):
        if upper_band[i - 1].is_nan() or lower_band[i - 1].is_nan():
            continue
        cur_st = supertrend[i]
        if trend == -1 and cur_st > supertrend[i - 1] and cur_st > lower_band[i]:
            trend = 1
        if trend == 1 and cur_st < supertrend[i - 1] and cur_st < upper_band[i]:
            trend = -1
        if trend == 1:
            supertrend[i] = max(lower_band[i], supertrend[i - 1])
        if trend == -1:
            supertrend[i] = min(upper_band[i], supertrend[i - 1])

    # print(len(supertrend[(supertrend > upper_band.shift(1)) & (supertrend > lower_band)]))
    # print(len(supertrend[(supertrend < lower_band.shift(1)) & (supertrend < upper_band)]))
    # supertrend[(supertrend > upper_band.shift(1)) & (supertrend > lower_band)] = upper_band[(supertrend > upper_band.shift(1)) & (supertrend > lower_band)]
    # supertrend[(supertrend < lower_band.shift(1)) & (supertrend < upper_band)] = lower_band[(supertrend < lower_band.shift(1)) & (supertrend < upper_band)]

    # fig.add_trace(go.Scatter(x=df['Datetime'], y=lower_band,
    #                          mode='lines', name='lower_band', line=dict(color='black', width=1)), row=1, col=1)
    # fig.add_trace(go.Scatter(x=df['Datetime'], y=upper_band,
    #                          mode='lines', name='upper_band', line=dict(color='green', width=1)), row=1, col=1)

    df["supertrend"] = supertrend
    df["lower_band"] = lower_band
    df["upper_band"] = upper_band
    fig.add_trace(go.Scatter(x=df['Datetime'], y=supertrend,
                             mode='markers', name='SuperTrend', line=dict(color='orange', width=1)), row=1, col=1)

    df.to_csv("data.csv")
    fig.show()
