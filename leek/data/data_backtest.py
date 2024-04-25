#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:09
# @Author  : shenglin.li
# @File    : data_backtest.py
# @Software: PyCharm
import json
import sqlite3
from decimal import Decimal

from leek.common import EventBus, logger, config, G
from leek.common.utils import decimal_quantize, decimal_to_str
from leek.data.data import DataSource


class BacktestDataSource(DataSource):
    verbose_name = "回测数据源"

    def __init__(self, interval: str, symbols: [], start_time: int, end_time: int, benchmark: str = None):
        self.keep_running = True
        self.interval = interval
        self.symbols = symbols
        if benchmark:
            self.symbols.append(benchmark)
        self.start_time = start_time
        self.end_time = end_time
        self.count = None

    def _ck_run(self):
        from clickhouse_driver import Client
        args = {
            "host": config.KLINE_DB_HOST,
            "port": config.KLINE_DB_PORT,
            "database": config.KLINE_DB_DATABASE,
            "user": config.KLINE_DB_USER,
        }
        if config.KLINE_DB_PASSWORD and config.KLINE_DB_PASSWORD != "":
            args["password"] = config.KLINE_DB_PASSWORD
        client = Client(**args)
        sql = f"select count(*) from workstation_kline" \
              f" where interval='{self.interval.lower()}' and timestamp >= {self.start_time} and timestamp <= " \
              f"{self.end_time} and symbol in (%s)" % \
              (",".join(["'%s'" % symbol for symbol in self.symbols]))
        self.count = client.execute(query=sql)[0][0]

        sql = sql.replace("count(*)", "timestamp,symbol,open,high,low,close,volume,amount")
        sql += " order by timestamp"
        cursor = client.execute_iter(sql)
        return None, cursor

    def _sqlite_run(self):
        conn = sqlite3.connect(config.KLINE_DB_PATH)
        cursor = conn.cursor()
        sql = f"select count(*) from workstation_kline" \
              f" where interval='{self.interval.lower()}' and timestamp >= {self.start_time} and timestamp <= " \
              f"{self.end_time} and symbol in (%s) order by timestamp" % \
              (",".join(["'%s'" % symbol for symbol in self.symbols]))
        cursor.execute(sql)
        self.count = cursor.fetchone()[0]

        sql = sql.replace("count(*)", "timestamp,symbol,open,high,low,close,volume,amount")
        cursor.execute(sql)

        def generator():
            while rows := cursor.fetchmany(200):
                for row in rows:
                    yield row
            cursor.close()

        return conn, generator()

    def _run(self):
        try:
            conn, cursor = None, None
            if config.KLINE_DB_TYPE == "CLICKHOUSE":
                conn, cursor = self._ck_run()
            elif config.KLINE_DB_TYPE == "SQLITE":
                conn, cursor = self._sqlite_run()

            cur = 0
            last = 0
            for row in cursor:
                if not self.keep_running:
                    break
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
            if conn:
                conn.close()
        self.bus.publish("backtest_data_source_process", 95)
        self.bus.publish("backtest_data_source_done", "回测数据源已关闭")


def shutdown(self):
    self.keep_running = False


if __name__ == '__main__':
    # select * from workstation_kline where `symbol`="ETHUSDT"  and timestamp between 1703132100000 and 1703337300000 and interval='15m'
    source = BacktestDataSource("15m", ["ETHUSDT"], 1703132100000, 1703337300000)
    bus = EventBus()
    data = []
    bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: data.append(x.__json__()))
    DataSource.__init__(source, bus)
    source._run()
    print(json.dumps(data, default=decimal_to_str))
    # source.shutdown()
