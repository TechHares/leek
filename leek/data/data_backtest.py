#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:09
# @Author  : shenglin.li
# @File    : data_backtest.py
# @Software: PyCharm
import os
from decimal import Decimal

import pandas as pd

from leek.common import EventBus, logger
from leek.data.data import DataSource

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H5_DATA = os.path.join(PROJECT_PATH, "resources/h5data")


class BacktestDataSource(DataSource):
    def __init__(self, interval: str, symbols: [], start_time: int, end_time: int, benchmark: str = None):
        self.keep_running = True
        self.interval = interval
        self.symbols = symbols
        if benchmark:
            self.symbols.append(benchmark)
        self.start_time = start_time
        self.end_time = end_time
        self.count = None

    def _run(self):
        filename = os.path.join(H5_DATA, f"{self.interval}.hdf5")
        with pd.HDFStore(filename, "r") as h5:
            df = pd.concat(map(h5.get, [symbol for symbol in self.symbols if "/" + symbol in h5.keys()]), axis=0)
            df = df[(self.start_time <= df.timestamp) & (df.timestamp <= self.end_time)]
            df.sort_values("timestamp", inplace=True)
            self.count = df.shape[0]
            cur = 0
            last = 0
            for index, row in df.iterrows():
                cur += 1
                process = int(cur * 1.0 / self.count * 90)
                if process != last:
                    last = process
                    self.bus.publish("backtest_data_source_process", process)
                if not self.keep_running:
                    logger.info("回测数据源已关闭")
                    break
                self._send_tick_data({
                    "symbol": row.loc["symbol"],
                    "timestamp": row.loc["timestamp"],
                    "open": Decimal(row.loc["open"]),
                    "high": Decimal(row.loc["high"]),
                    "low": Decimal(row.loc["low"]),
                    "close": Decimal(row.loc["close"]),
                    "volume": Decimal(row.loc["volume"]),
                    "amount": Decimal(row.loc["amount"]),
                    "finish": 1,
                })

        self.bus.publish("backtest_data_source_process", 95)
        self.bus.publish("backtest_data_source_done", "回测数据源已关闭")

    def shutdown(self):
        self.keep_running = False


if __name__ == '__main__':
    source = BacktestDataSource("30m", ["BTCUSDT", "ETHUSDT"], "2023-10-01", "2023-11-01")
    DataSource.__init__(source, EventBus())
    source.start()
    source.shutdown()
