#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/26 10:59
# @Author  : shenglin.li
# @File    : strategy_mean_test.py
# @Software: PyCharm
import unittest
from decimal import Decimal

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
import plotly.graph_objs as go

from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common import SymbolsFilter, PositionDirectionManager, CalculatorContainer, AtrStopLoss
from leek.strategy.strategy_mean import SingleMaStrategy, LLTStrategy
from leek.trade.trade import PositionSide


class TestMean(unittest.TestCase):
    def test_llthandle(self):
        strategy = LLTStrategy()
        PositionDirectionManager.__init__(strategy, PositionSide.FLAT)
        PositionRateManager.__init__(strategy, "1")
        self.bus = EventBus()
        workflow = ViewWorkflow(strategy, "4h", 1704124800000, 1715159848986, "BTCUSDT")
        # workflow = ViewWorkflow(strategy, "1d", 1199116800000, 1716369864986, "600031", 1)
        # workflow = ViewWorkflow(strategy, "1d", 1514736000600, 1716369864986, "399967", 1)

        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        # 添加开仓通道
        df['ma'] = df['close'].rolling(window=20).mean().apply(lambda x: Decimal(x))
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['llt'], mode='lines', name='LLT'), row=1, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['ma'], mode='lines', name='MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['llt2'], mode='lines', name='LLT2'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', name='斜率'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['balance'], mode='lines', name='斜率'), row=3, col=1)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

if __name__ == '__main__':

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
