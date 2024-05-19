#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:26
# @Author  : shenglin.li
# @File    : script_binance_data_download.py
# @Software: PyCharm
import argparse
import datetime
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import django
import tqdm
from okx import MarketData

root = Path(__file__).resolve().parent.parent.parent
if root in sys.path:
    sys.path.remove(f"{root}")
sys.path.append(f'{Path(__file__).resolve().parent.parent}')
sys.path.append(f'{root}')


def check_kline(start_date, end_date, symbols=None, intervals=None, skip=0):
    if intervals is None:
        intervals = ["1h", "4h", "6h", "12h", "1m", "3m", "5m", "15m", "30m", "1d"]
    if symbols is None or len(symbols) == 0:
        from django.db import connections
        with connections["data"].cursor() as cursor:
            cursor.execute("select distinct symbol from workstation_kline order by symbol")
            rows = cursor.fetchall()
            symbols = [row[0] for row in rows]
    print(symbols)
    i = 0
    end_ts = int(datetime.datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000) + 24 * 60 * 60 * 1000
    start_ts = int(datetime.datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    print(start_ts, end_ts)
    n = 100 * 24 * 60 * 60 * 1000
    time_intervals = [[start_ts + n * i, min(start_ts + n * i + n, end_ts)] for i in range((end_ts - start_ts)//n + 1)]
    tf = lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M')
    bar = tqdm.tqdm(total=len(symbols) * len(intervals) * len(time_intervals), desc="数据校验")
    for time_interval in time_intervals:
        for symbol in symbols:
            i += 1
            if i < skip:
                continue
            check_symbol(symbol, time_interval[0], time_interval[1], intervals, bar)


def check_symbol(symbol, start_ts, end_ts, intervals, bar=None):

    tf = lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M')
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
    from .models import Kline
    datas = Kline.objects.filter(symbol=symbol, interval="1m", timestamp__gte=start_ts, timestamp__lt=end_ts).order_by(
        "timestamp")
    for interval in intervals:
        bar.update(1)
        if interval == "1m":
            continue
        check_data = Kline.objects.filter(symbol=symbol, interval=interval, timestamp__gte=start_ts,
                                          timestamp__lt=end_ts)
        bar.set_postfix_str(f"{symbol} {interval}")
        for data in check_data:
            end = data.timestamp + config_interval[interval] - config_interval["1m"]
            valid_data = find_aggregate_bar(datas, data.timestamp, end)
            if valid_data is None:
                print(f"{symbol} {interval} {tf(data.timestamp)} 数据缺失")
                continue
            if len(valid_data) != config_interval[interval] // config_interval["1m"]:
                print(f"{symbol} {interval} {tf(data.timestamp)} 长度不正确")
            if compare_fail(data.open, valid_data[0].open):
                print(f"{symbol} {interval} {tf(data.timestamp)} open {data.open} != {valid_data[0].open}")
            if compare_fail(data.close, valid_data[-1].close):
                print(f"{symbol} {interval} {tf(data.timestamp)} close {data.close} != {valid_data[-1].close}")
            if compare_fail(data.high, max([d.high for d in valid_data])):
                print(f"{symbol} {interval} {tf(data.timestamp)} high {data.high} != {max([d.high for d in valid_data])}")
            if compare_fail(data.low, min([d.low for d in valid_data])):
                print(f"{symbol} {interval} {tf(data.timestamp)} low {data.low} != {min([d.low for d in valid_data])}")

            vol = sum([d.volume for d in valid_data])
            if compare_fail(data.volume, vol):
                print(f"{symbol} {interval} {tf(data.timestamp)} volume {data.volume} != {vol}")

            amt = sum([d.amount for d in valid_data])
            if compare_fail(data.amount, amt):
                print(f"{symbol} {interval} {tf(data.timestamp)} amount {data.amount} != {amt}")


def compare_fail(a, b):
    if a == b:
        return False

    if b is None or b == 0:
        return True

    return abs(1 - a / b) < 0.01


def find_aggregate_bar(data, start_ts, end_ts):
    left = binary_search(data, start_ts)
    right = binary_search(data, end_ts)
    if left == -1 or right == -1:
        return None
    return data[left:right + 1]


def binary_search(sorted_list, target):
    left, right = 0, len(sorted_list) - 1
    while left <= right:
        mid = (left + right) // 2
        if sorted_list[mid].timestamp == target:
            return mid
        elif sorted_list[mid].timestamp < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    os.environ.setdefault("DISABLE_WORKER", "true")
    django.setup()
    __package__ = "workstation"

    parser = argparse.ArgumentParser(description='OKX行情下载参数')

    # 定义期望接收的参数
    parser.add_argument('--start', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--end', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--symbols', type=lambda x: x.split(','), default=[])
    parser.add_argument('--interval', type=lambda x: x.split(','),
                        default=["1h", "4h", "6h", "12h", "1m", "3m", "5m", "15m", "30m", "1d"])
    parser.add_argument('--skip', type=int, default=0)
    args = parser.parse_args()
    print("    start:", args.start)
    print("      end:", args.end)
    print("  symbols:", args.symbols)
    print(" interval:", args.interval)
    print("     skip:", args.skip)

    check_kline(args.start, args.end, symbols=args.symbols, intervals=args.interval, skip=args.skip)

    # python script_okx_data_download.py --start=2024-03-01 --end=2024-04-02 --interval=5m --skip=7
