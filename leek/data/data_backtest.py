#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:09
# @Author  : shenglin.li
# @File    : data_backtest.py
# @Software: PyCharm
import sqlite3
from decimal import Decimal

from leek.common import EventBus, logger, config, G
from leek.data.data import DataSource


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
        db_file = f"{config.KLINE_DIR}/{self.interval}.db"

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            sql = f"select count(*) from workstation_kline" \
                  f" where timestamp >= {self.start_time} and timestamp <= " \
                  f"{self.end_time} and symbol in (%s) order by timestamp" % \
                  (",".join(["'%s'" % symbol for symbol in self.symbols]))
            cursor.execute(sql)
            self.count = cursor.fetchone()[0]
            cur = 0
            last = 0

            sql = sql.replace("count(*)", "timestamp,symbol,open,high,low,close,volume,amount")
            cursor.execute(sql)
            while rows := cursor.fetchmany(200):
                if not self.keep_running:
                    break
                # 处理每批次的数据
                for row in rows:
                    cur += 1
                    process = int(cur * 1.0 / self.count * 90)
                    if process != last:
                        last = process
                        self.bus.publish("backtest_data_source_process", process)
                    if not self.keep_running:
                        logger.info("回测数据源已关闭")
                        break
                    self._send_tick_data(G(symbol=row[1],
                                           timestamp=row[0],
                                           open=Decimal(row[2]),
                                           high=Decimal(row[3]),
                                           low=Decimal(row[4]),
                                           close=Decimal(row[5]),
                                           volume=Decimal(row[6]),
                                           amount=Decimal(row[7]),
                                           finish=1
                                           ))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        self.bus.publish("backtest_data_source_process", 95)
        self.bus.publish("backtest_data_source_done", "回测数据源已关闭")


def shutdown(self):
    self.keep_running = False


if __name__ == '__main__':
    source = BacktestDataSource("30m", ["BTCUSDT", "ETHUSDT"], 1674544707299, 1706080707299)
    DataSource.__init__(source, EventBus())
    source.start()
    source.shutdown()
