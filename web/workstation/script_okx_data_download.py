#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:26
# @Author  : shenglin.li
# @File    : script_binance_data_download.py
# @Software: PyCharm
import argparse
import csv
import datetime
import json
import shutil
import sys
import time
from decimal import Decimal
from pathlib import Path
import os

import django
import requests
import tqdm
from okx import MarketData

root = Path(__file__).resolve().parent.parent.parent
if root in sys.path:
    sys.path.remove(f"{root}")
sys.path.append(f'{Path(__file__).resolve().parent.parent}')
sys.path.append(f'{root}')

from leek.common import IdGenerator, config

generator = IdGenerator(1)
api = MarketData.MarketAPI(domain="https://aws.okx.com", flag="0", debug=False, proxy=config.PROXY)


def download_okx_kline(start_date, end_date, symbols=None, intervals=None, skip=0, inst_type="SWAP"):
    if intervals is None:
        intervals = ["1H", "4H", "6H", "12H", "1m", "3m", "5m", "15m", "30m", "1D"]
    if symbols is None or len(symbols) == 0:
        tickers = api.get_tickers(instType=inst_type)
        symbols = []
        if tickers and tickers["code"] == "0":
            for ticker in tickers["data"]:
                if ticker["instId"].endswith("-USDT-" + inst_type):
                    symbols.append(ticker["instId"])
    bar = tqdm.tqdm(total=len(symbols), desc="OKX数据")
    print(symbols)
    for symbol in symbols:
        bar.update(1)
        if bar.n < skip:
            continue
        __download_okx_kline(symbol, start_date, end_date, intervals, bar)


def __download_okx_kline(symbol, start_date, end_date, intervals, bar=None):
    end_ts = int(datetime.datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000) + 24 * 60 * 60 * 1000
    hour = 60 * 60 * 1000
    multi = {
        "1m": 1.5,
        "3m": 5,
        "5m": 8,
        "15m": 24,
        "30m": 50,
        "1H": 100,
        "4H": 400,
        "6H": 600,
        "12H": 1200,
        "1D": 2400,
    }
    tf = lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M')
    for interval in intervals:
        start_ts = find_real_start_ts(symbol, interval,
                                      int(datetime.datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000),
                                      end_ts, int(hour * multi[interval]))
        while start_ts < end_ts:
            n = start_ts + int(hour * multi[interval])
            if bar:
                bar.set_postfix_str(f"{symbol} {interval} {tf(start_ts)} {tf(n)}")

            rows = get_data(symbol, interval, start_ts, n, bar=bar)
            rows.reverse()
            save_data(symbol, interval, rows)
            start_ts = n


def find_real_start_ts(symbol, interval, start_ts, end_ts, step):
    if (end_ts - start_ts) / step < 50:
        return start_ts
    max_find = 16
    left, right = start_ts, end_ts
    while max_find > 0 and left < right:
        max_find -= 1
        middle = int((left + right) / 2)
        rows = get_data(symbol, interval, left, middle)
        if len(rows) == 0:
            left = middle
        elif len(rows) == 100:
            right = middle
        else:
            break
    return left


def get_data(symbol, interval, start_ts, n, t=5, bar=None):
    try:
        candlesticks = api.get_history_candlesticks(symbol, before="%s" % (start_ts - 1), after="%s" % n,
                                                    bar=interval)
        if candlesticks is None or candlesticks["code"] != "0":
            if candlesticks:
                if bar:
                    bar.set_postfix_str(f"{symbol} {interval} {candlesticks['msg']}")
            raise Exception(candlesticks["msg"] if candlesticks else candlesticks)
        return candlesticks["data"]
    except Exception as e:
        if t > 0:
            time.sleep(0.5)
            return get_data(symbol, interval, start_ts, n, t - 1)
        else:
            raise e


def save_data(symbol, interval, rows):
    from .models import Kline
    datas = [Kline(
        id=generator.next(),
        interval=interval.lower(),
        timestamp=int(row[0]),
        symbol=symbol,
        open=Decimal(row[1]),
        high=Decimal(row[2]),
        low=Decimal(row[3]),
        close=Decimal(row[4]),
        volume=Decimal(row[5]),
        amount=Decimal(row[7]),
    ) for row in rows if int(row[8]) == 1]
    Kline.objects.bulk_create(datas)


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    os.environ.setdefault("DISABLE_WORKER", "true")
    django.setup()
    __package__ = "workstation"

    parser = argparse.ArgumentParser(description='OKX行情下载参数')

    # 定义期望接收的参数
    parser.add_argument('--start', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--end', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--inst_type', type=str, default="SWAP")
    parser.add_argument('--symbols', type=lambda x: x.split(','), default=[])
    parser.add_argument('--interval', type=lambda x: x.split(','),
                        default=["1H", "4H", "6H", "12H", "1m", "3m", "5m", "15m", "30m", "1D"])
    parser.add_argument('--skip', type=int, default=0)
    args = parser.parse_args()
    print("    start:", args.start)
    print("      end:", args.end)
    print("inst_type:", args.inst_type)
    print("  symbols:", args.symbols)
    print(" interval:", args.interval)
    print("     skip:", args.skip)

    download_okx_kline(args.start, args.end, symbols=args.symbols, intervals=args.interval, skip=args.skip,
                       inst_type=args.inst_type)
    # python script_okx_data_download.py --start=2024-03-01 --end=2024-04-02 --interval=5m --skip=7
