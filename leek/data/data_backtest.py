#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:09
# @Author  : shenglin.li
# @File    : data_backtest.py
# @Software: PyCharm
import json
import random
import sqlite3
from datetime import datetime
from decimal import Decimal
import efinance as ef

from leek.common import EventBus, logger, config, G
from leek.common.utils import decimal_quantize, decimal_to_str, DateTime
from leek.data.data import DataSource
import warnings

warnings.simplefilter('ignore', ResourceWarning)
config_interval = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


class BacktestDataSource(DataSource):
    verbose_name = "回测数据源"

    def __init__(self, interval: str, symbols: [], start_time: int, end_time: int, benchmark: str = None):
        self.interval = interval.lower()
        self.symbols = symbols
        if benchmark and benchmark not in self.symbols:
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
              f" where interval in [{self._emulation_interval()}] and timestamp >= {self.start_time} and timestamp <= " \
              f"{self.end_time} and symbol in (%s)" % \
              (",".join(["'%s'" % symbol for symbol in self.symbols]))
        self.count = client.execute(query=sql)[0][0]

        sql = sql.replace("count(*)", "timestamp,symbol,open,high,low,close,volume,amount,interval,"
                                      "timestamp + multiIf(interval='1m', 60000, interval='3m', 180000, interval='5m',"
                                      "300000, interval='15m', 900000, interval='30m', 1800000, interval='1h', 3600000,"
                                      "interval='4h', 14400000, interval='6h', 21600000, interval='8h', 28800000,"
                                      " interval='12h', 43200000, interval='1d', 86400000, 0) end_timestamp")
        sql += " order by end_timestamp"
        cursor = client.execute_iter(sql)
        return None, cursor

    def _emulation_interval(self):
        if config.BACKTEST_EMULATION and self.interval == config.BACKTEST_TARGET_INTERVAL:
            return "'%s', '%s'" % (self.interval, config.BACKTEST_EMULATION_INTERVAL)
        return "'%s'" % self.interval

    def _sqlite_run(self):
        conn = sqlite3.connect(config.KLINE_DB_PATH)
        cursor = conn.cursor()
        sql = f"select count(*) from workstation_kline" \
              f" where interval in ({self._emulation_interval()}) and timestamp >= {self.start_time} and timestamp <= " \
              f"{self.end_time} and symbol in (%s) order by timestamp" % \
              (",".join(["'%s'" % symbol for symbol in self.symbols]))
        cursor.execute(sql)
        self.count = cursor.fetchone()[0]

        sql = sql.replace("count(*)", "timestamp,symbol,open,high,low,close,volume,amount,interval, timestamp + CASE "
                                      " WHEN interval='1m' THEN 60000"
                                      " WHEN interval='3m' THEN 180000"
                                      " WHEN interval='5m' THEN 300000"
                                      " WHEN interval='15m' THEN 900000"
                                      " WHEN interval='30m' THEN 1800000"
                                      " WHEN interval='1h' THEN 3600000"
                                      " WHEN interval='4h' THEN 14400000"
                                      " WHEN interval='6h' THEN 21600000"
                                      " WHEN interval='8h' THEN 28800000"
                                      " WHEN interval='12h' THEN 43200000"
                                      " WHEN interval='1d' THEN 86400000"
                                      " ELSE 0"
                                      " END"
                                      " end_timestamp")
        cursor.execute(sql)

        def generator():
            while rows := cursor.fetchmany(200):
                for row in rows:
                    yield row
            cursor.close()

        return conn, generator()

    def get_all_symbol(self):
        sql = "select distinct symbol from workstation_kline"
        if config.KLINE_DB_TYPE == "CLICKHOUSE":
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
            res = client.execute(sql)
            return [a[0] for a in res]
        elif config.KLINE_DB_TYPE == "SQLITE":
            conn = sqlite3.connect(config.KLINE_DB_PATH)
            cursor = conn.cursor()
            return [a[0] for a in cursor.fetchall()]

    def _run(self):
        try:
            conn, cursor = None, None
            if config.KLINE_DB_TYPE == "CLICKHOUSE":
                conn, cursor = self._ck_run()
            elif config.KLINE_DB_TYPE == "SQLITE":
                conn, cursor = self._sqlite_run()

            cur = 0
            last = 0
            batch = []
            emulation_map = {}

            def send_data():
                nonlocal batch
                if len(batch) > 0:
                    random.shuffle(batch)
                    for b in batch:
                        self._send_tick_data(b)
                    batch = []

            ts = 0
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
                if ts != row[0]:
                    send_data()
                    ts = row[0]
                ticket = G(symbol=row[1], timestamp=row[0], open=Decimal(row[2]), high=Decimal(row[3]), current_time=row[0],
                           low=Decimal(row[4]), close=Decimal(row[5]), volume=Decimal(row[6]), amount=Decimal(row[7]),
                           interval=row[8], finish=0 if config.BACKTEST_EMULATION and row[
                        8] == config.BACKTEST_EMULATION_INTERVAL else 1)
                if config.BACKTEST_EMULATION and self.interval == config.BACKTEST_TARGET_INTERVAL:
                    if config.BACKTEST_TARGET_INTERVAL == ticket.interval:  # K线
                        if ticket.symbol in emulation_map:
                            del emulation_map[ticket.symbol]
                    else:
                        if ticket.symbol not in emulation_map:
                            emulation_map[ticket.symbol] = G(**ticket.__json__())
                        else:
                            t = emulation_map[ticket.symbol]
                            t.close = ticket.close
                            t.high = max(t.high, ticket.high)
                            t.low = min(t.low, ticket.low)
                            t.volume += ticket.volume
                            t.amount += ticket.amount
                            t.cur_timestamp = ticket.timestamp
                            t.timestamp = ticket.timestamp - ticket.timestamp % config_interval[self.interval]
                            ticket = G(**t.__json__())

                ticket.interval = self.interval
                batch.append(ticket)

            cursor.close()
            send_data()
        finally:
            if conn:
                conn.close()
        self.bus.publish("backtest_data_source_process", 95)
        self.bus.publish("backtest_data_source_done", "回测数据源已关闭")


class StockBacktestDataSource(BacktestDataSource):
    verbose_name = "回测数据源(股票)"

    def __init__(self):
        self.interval_map = {
            # "1m": 1,
            # "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "1d": 101,
            "1W": 102,
            "1M": 103,
        }

    def _run(self):
        if self.interval not in self.interval_map:
            self.bus.publish(EventBus.TOPIC_RUNTIME_ERROR, "不支持的周期")
        beg = datetime.fromtimestamp(self.start_time / 1000).strftime('%Y%m%d')
        end = datetime.fromtimestamp(self.end_time / 1000).strftime('%Y%m%d')

        def next_tick(itrows):
            i, row = next(itrows, (None, None))
            if row is None:
                return None
            return G(symbol=row["股票代码"],
                     current_time=DateTime.to_timestamp(row["日期"]),
                     timestamp=DateTime.to_timestamp(row["日期"]),
                     open=Decimal(str(row["开盘"])),
                     high=Decimal(str(row["最高"])),
                     low=Decimal(str(row["最低"])),
                     close=Decimal(str(row["收盘"])),
                     volume=Decimal(str(row["成交量"])),
                     amount=Decimal(str(row["成交额"])),
                     finish=1
                     )

        history = ef.stock.get_quote_history(self.symbols, klt=self.interval_map[self.interval], beg=beg, end=end)

        if isinstance(history, dict):
            dfs = [x.iterrows() for x in history.values()]
            it = [next_tick(x) for x in dfs]
            random.shuffle(dfs)
            while any([x is not None for x in it]) and self.keep_running:
                min_ts = min([x.timestamp for x in it if x is not None])
                for idx in range(len(it)):
                    if it[idx] is not None and it[idx].timestamp == min_ts:
                        self._send_tick_data(it[idx])
                        it[idx] = next_tick(dfs[idx])
        else:
            iterrows = history.iterrows()
            while (x := next_tick(iterrows)) is not None and self.keep_running:
                self._send_tick_data(x)


if __name__ == '__main__':
    # select * from workstation_kline where `symbol`="ETHUSDT"  and timestamp between 1703132100000 and 1703337300000 and interval='15m'
    source = BacktestDataSource("4h", ["ETHUSDT"], 1703132100000, 1703337300000)
    bus = EventBus()
    data = []
    bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: data.append(x.__json__()))
    DataSource.__init__(source, bus)
    source._run()
    for d in data:
        print(d["symbol"], datetime.fromtimestamp(d["timestamp"] / 1000).strftime("%Y-%m-%d %H:%M"), d["interval"],
              d["close"], d["volume"], d["amount"])
    # print(json.dumps(data, default=decimal_to_str))
    # source.shutdown()
