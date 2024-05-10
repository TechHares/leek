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
from leek.common.utils import decimal_quantize, decimal_to_str
from leek.data.data import DataSource
import warnings

warnings.simplefilter('ignore', ResourceWarning)


class BacktestDataSource(DataSource):
    verbose_name = "回测数据源"

    def __init__(self, interval: str, symbols: [], start_time: int, end_time: int, benchmark: str = None):
        self.interval = interval
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
            batch = []

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

                batch.append(G(symbol=row[1],
                               timestamp=row[0],
                               open=Decimal(row[2]),
                               high=Decimal(row[3]),
                               low=Decimal(row[4]),
                               close=Decimal(row[5]),
                               volume=Decimal(row[6]),
                               amount=Decimal(row[7]),
                               finish=1
                               ))

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

        def to_ts(x):
            if len(x) == 10:
                return int(datetime.strptime(x, '%Y-%m-%d').timestamp() * 1000)
            if len(x) == 16:
                return int(datetime.strptime(x, '%Y-%m-%d %H:%M').timestamp() * 1000)
            return int(datetime.strptime(x, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)

        def next_tick(itrows):
            i, row = next(itrows, (None, None))
            if row is None:
                return None
            return G(symbol=row["股票代码"],
                     timestamp=to_ts(row["日期"]),
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
    source = BacktestDataSource("15m", ["ETHUSDT"], 1703132100000, 1703337300000)
    bus = EventBus()
    data = []
    bus.subscribe(EventBus.TOPIC_TICK_DATA, lambda x: data.append(x.__json__()))
    DataSource.__init__(source, bus)
    source._run()
    print(json.dumps(data, default=decimal_to_str))
    # source.shutdown()
