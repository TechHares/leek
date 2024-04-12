#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/19 20:42
# @Author  : shenglin.li
# @File    : view.py
# @Software: PyCharm
from decimal import Decimal

import cachetools

from leek.common import EventBus, config, G
from leek.data import BacktestDataSource, DataSource
from leek.runner.runner import BaseWorkflow
from leek.strategy import BaseStrategy
from leek.trade import Trader
from leek.trade.trade_backtest import BacktestTrader
import pandas as pd


class ViewWorkflow(BaseWorkflow):
    def __init__(self, strategy, interval: str, start_time: int, end_time: int, symbol):
        BaseWorkflow.__init__(self, "V0")
        self.interval = interval
        self.strategy = strategy
        self.start_time = start_time
        self.end_time = end_time
        self.benchmark = symbol

        self.kline_data = []
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
    def get_data(self):
        self.data_source = BacktestDataSource(self.interval, [], self.start_time, self.end_time, self.benchmark)
        DataSource.__init__(self.data_source, self.bus)
        conn, cursor = None, None
        if config.KLINE_DB_TYPE == "CLICKHOUSE":
            conn, cursor = self.data_source._ck_run()
        elif config.KLINE_DB_TYPE == "SQLITE":
            conn, cursor = self.data_source._sqlite_run()

        return [G(symbol=row[1],
                  timestamp=row[0],
                  open=Decimal(row[2]),
                  high=Decimal(row[3]),
                  low=Decimal(row[4]),
                  close=Decimal(row[5]),
                  volume=Decimal(row[6]),
                  amount=Decimal(row[7]),
                  finish=1
                  ).__json__() for row in cursor]

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
    def get_data_g(self):
        return [G(**row) for row in self.get_data()]

    def handle_data(self):
        for row in self.get_data():
            data = G(symbol=row["symbol"],
                     timestamp=row["timestamp"],
                     open=row["open"],
                     high=row["high"],
                     low=row["low"],
                     close=row["close"],
                     volume=row["volume"],
                     amount=row["amount"],
                     finish=1
                     )
            js = data.__json__()
            self.kline_data.append(js)
            self.data_source._send_tick_data(data)

    def draw(self, fig=None, row=1, col=1, df=None):
        import plotly.graph_objs as go
        from plotly.subplots import make_subplots

        if df is None:
            df = pd.DataFrame(self.kline_data)
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
        return fig


if __name__ == '__main__':
    pass
