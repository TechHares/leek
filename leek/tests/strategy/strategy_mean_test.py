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



if __name__ == '__main__':
    from leek.strategy.common import SymbolsFilter, PositionDirectionManager, CalculatorContainer, AtrStopLoss
    from leek.strategy.strategy_mean import SingleMaStrategy

    strategy = SingleMaStrategy()
    workflow = ViewWorkflow(strategy, "5m", 1710000000000, 1710259200000, "ZRXUSDT")
    workflow.start()
    df = pd.DataFrame(workflow.kline_data)
    df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig = workflow.draw(fig=fig, df=df, row=1)
    workflow.draw(fig=fig, df=df)

    df['ma_amount'] = df['amount'].rolling(window=strategy.period).mean()
    df['ma_volume'] = df['volume'].rolling(window=strategy.period).mean()
    df['ma'] = (df['ma_amount'] / df['ma_volume']).apply(lambda x: Decimal(x))
    # df['avg_price'] = df['amount'] / df['volume']
    # df['ma_fast'] = df['avg_price'].rolling(window=5).mean().apply(lambda x: Decimal(x))
    # df['ma_slow'] = df['avg_price'].rolling(window=20).mean().apply(lambda x: Decimal(x))
    # df['ma_long'] = df['avg_price'].rolling(window=60).mean().apply(lambda x: Decimal(x))
    # 添加 ma 指标
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma'],
                             mode='lines', name='ma', line=dict(color='orange', width=1)), row=1, col=1)
    # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma_long'],
    #                          mode='lines', name='ma_long', line=dict(color='red', width=1)), row=1, col=1)
    fig.show()
