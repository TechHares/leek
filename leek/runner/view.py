#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/19 20:42
# @Author  : shenglin.li
# @File    : view.py
# @Software: PyCharm
from decimal import Decimal

import cachetools

from leek.common import EventBus, config, G
from leek.common.utils import DateTime
from leek.data import BacktestDataSource, DataSource
from leek.data.data_backtest import StockBacktestDataSource
from leek.runner.runner import BaseWorkflow
from leek.strategy import BaseStrategy
from leek.trade import Trader
from leek.trade.trade_backtest import BacktestTrader
import pandas as pd


class ViewWorkflow(BaseWorkflow):
    def __init__(self, strategy, interval: str, start_time, end_time, symbol, data_source_type=0):
        BaseWorkflow.__init__(self, "V0")
        self.interval = interval
        self.strategy = strategy
        if isinstance(start_time, str):
            start_time = DateTime.to_timestamp(start_time)
        if isinstance(end_time, str):
            end_time = DateTime.to_timestamp(end_time)
        self.start_time = start_time
        self.end_time = end_time
        self.benchmark = symbol
        self.data_source_type = data_source_type

        self.kline_data_g = []
        self.open_long = []
        self.open_short = []
        self.close_long = []
        self.close_short = []

    def start(self):
        self.trader = BacktestTrader()
        Trader.__init__(self.trader, self.bus)

        BaseStrategy.__init__(self.strategy, "V0", self.bus, "1000")

        self.bus.subscribe(EventBus.TOPIC_STRATEGY_SIGNAL, self.mark_data)
        self.handle_data()

    def mark_data(self, sig):
        if sig.signal_name == "OPEN_LONG":
            self.open_long.append(sig.timestamp)
        elif sig.signal_name == "OPEN_SHORT":
            self.open_short.append(sig.timestamp)
        elif sig.signal_name == "CLOSE_LONG":
            self.close_long.append(sig.timestamp)
        elif sig.signal_name == "CLOSE_SHORT":
            self.close_short.append(sig.timestamp)

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
    def get_data(self, benchmark: str):
        data = []
        bus = EventBus()
        if self.data_source_type == 1:
            self.data_source = StockBacktestDataSource()
            DataSource.__init__(self.data_source, bus)
            BacktestDataSource.__init__(self.data_source, self.interval, [], self.start_time, self.end_time, benchmark)
        else:
            self.data_source = BacktestDataSource(self.interval, [], self.start_time, self.end_time, benchmark)
            DataSource.__init__(self.data_source, bus)

        bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: data.append(x))
        self.data_source._run()
        self.data_source.bus = self.bus
        return data


    def handle_data(self):
        for data in self.get_data(self.benchmark):
            if data.finish == 1:
                self.kline_data_g.append(data)
            self.data_source._send_tick_data(data)
            data.balance = self.strategy.position_manager.get_value()

    def draw(self, fig=None, row=1, col=1, df=None):
        import plotly.graph_objs as go
        from plotly.subplots import make_subplots

        if df is None:
            df = pd.DataFrame([x.__json__() for x in self.kline_data_g])
            df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        # 创建 Plotly 子图
        if fig is None:
            fig = make_subplots(rows=1, cols=1, shared_xaxes=True)

        fig.add_trace(go.Candlestick(x=df['Datetime'],
                                     open=df['open'],
                                     high=df['high'],
                                     low=df['low'],
                                     close=df['close'], name=df.iloc[0]["symbol"]), row=1, col=1)
        # 添加 K 线图

        open_long = df[df["timestamp"].apply(lambda x: x in self.open_long)].index[0:]
        close_long = df[df["timestamp"].apply(lambda x: x in self.close_long)].index[0:]
        open_short = df[df["timestamp"].apply(lambda x: x in self.open_short)].index[0:]
        close_short = df[df["timestamp"].apply(lambda x: x in self.close_short)].index[0:]
        fig.add_trace(go.Scatter(
            x=df.loc[open_long, 'Datetime'],
            y=df.loc[open_long, 'low'] * Decimal("0.98"),
            mode='markers+text',
            text="开多",
            marker=dict(color='green', size=4)
        ), row=row, col=col)

        fig.add_trace(go.Scatter(
            x=df.loc[close_long, 'Datetime'],
            y=df.loc[close_long, 'high'] * Decimal("1.02"),
            mode='markers+text',
            text="平多",
            marker=dict(color='red', size=4)
        ), row=row, col=col)

        fig.add_trace(go.Scatter(
            x=df.loc[close_short, 'Datetime'],
            y=df.loc[close_short, 'low'] * Decimal("0.98"),
            mode='markers+text',
            text="平空",
            marker=dict(color='green', size=4)
        ), row=row, col=col)

        fig.add_trace(go.Scatter(
            x=df.loc[open_short, 'Datetime'],
            y=df.loc[open_short, 'high'] * Decimal("1.02"),
            mode='markers+text',
            text="开空",
            marker=dict(color='red', size=4)
        ), row=row, col=col)
        # 格式化图表
        fig.update_layout(
            title='K Line',
            xaxis_title='Date',
            yaxis_title='Price',
            legend_orientation="h",
        )
        return fig


if __name__ == '__main__':
    pass
