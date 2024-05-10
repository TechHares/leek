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
from decimal import Decimal
from pathlib import Path
import os

import django
import requests
import tqdm

root = Path(__file__).resolve().parent.parent.parent
if root in sys.path:
    sys.path.remove(f"{root}")
sys.path.append(f'{Path(__file__).resolve().parent.parent}')
sys.path.append(f'{root}')

from leek.common import IdGenerator

generator = IdGenerator(1)

PACK_INTERVAL = "monthly"  # daily/monthly


def download_binance_kline(start_date, end_date, symbols=None, intervals=None, skip=0):
    if intervals is None:
        intervals = ["1h", "4h", "6h", "8h", "12h", "1m", "3m", "5m", "15m", "30m", "1d"]
    if symbols is None or len(symbols) == 0:
        get = requests.post(
            "https://www.binance.com/bapi/bigdata/v1/public/bigdata/finance/exchange/listDownloadOptions",
            data=json.dumps({"bizType": "FUTURES_UM", "productId": 1}),
            headers={"Content-Type": "application/json"})
        symbols = [s for s in get.json()["data"]["symbolList"] if s.endswith("USDT")]
    bar = tqdm.tqdm(total=len(symbols), desc="币安行情数据")
    for symbol in symbols:
        bar.update(1)
        if bar.n < skip:
            continue
        __download_binance_kline(symbol, start_date, end_date, intervals, bar)


def __download_binance_kline(symbol, start_date, end_date, intervals, bar=None):
    from leek.common import config
    url = "https://www.binance.com/bapi/bigdata/v1/public/bigdata/finance/exchange/listDownloadData2"
    post = requests.post(url, data=json.dumps({
        "bizType": "FUTURES_UM",
        "productName": "klines",
        "symbolRequestItems": [{
            "endDay": end_date,
            "granularityList": intervals,
            "interval": PACK_INTERVAL,
            "startDay": start_date,
            "symbol": symbol
        }]
    }), headers={"Content-Type": "application/json"})
    item_list = post.json()["data"]["downloadItemList"]
    p = os.path.join(config.DOWNLOAD_DIR, "binance", symbol)
    if not os.path.exists(p):
        os.makedirs(p)
    for i in range(len(item_list)):
        item = item_list[i]
        filename = os.path.join(p, item["filename"])
        bar.set_postfix_str("下载 %s" % item["filename"])
        if not os.path.exists(filename):
            content = requests.get(item["url"], stream=True)
            with open(filename, "wb") as f:
                for d in content:
                    f.write(d)
        files = unzip_file(filename)
        bar.set_postfix_str("解压 %s" % item["filename"])
        for f in files:
            bar.set_postfix_str("入库 %s" % f)
            read_csv(p, f)


def unzip_file(file_path):
    import zipfile
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.dirname(file_path))
        return zip_ref.namelist()


def read_csv(file_dir, file):
    from .models import Kline
    symbol, interval = file.split('-')[0], file.split('-')[1]
    try:
        # # "id", "interval", "timestamp", "symbol", "open", "high", "low", "close", "volume", "amount"
        rows = [Kline(
            id=generator.next(),
            interval=interval,
            timestamp=int(row['open_time']),
            symbol=symbol,
            open=Decimal(row['open']),
            high=Decimal(row['high']),
            low=Decimal(row['low']),
            close=Decimal(row['close']),
            volume=Decimal(row['volume']),
            amount=Decimal(row['quote_volume']),
        ) for row in csv.DictReader(open(os.path.join(file_dir, file), 'r'))]
    except KeyError:
        rows = [Kline(
            id=generator.next(),
            interval=interval,
            timestamp=int(row['open_time']),
            symbol=symbol,
            open=Decimal(row['open']),
            high=Decimal(row['high']),
            low=Decimal(row['low']),
            close=Decimal(row['close']),
            volume=Decimal(row['volume']),
            amount=Decimal(row['quote_volume']),
        ) for row in csv.DictReader(open(os.path.join(file_dir, file), 'r'),
                                    fieldnames=["open_time", "open", "high", "low", "close", "volume", "close_time",
                                                "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume",
                                                "ignore"])]
    Kline.objects.bulk_create(rows)


def deal_bian_download_csv(path):
    all_files = [file for file in os.listdir(path) if file.endswith(".csv")]
    for file in all_files:
        read_csv(path, file)


def ods_2_dw(path):
    all_files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not os.path.exists(path + "dw"):
        os.mkdir(path + "dw")
    for file in all_files:
        with open(os.path.join(path, file), 'r', encoding="utf-8") as read, \
                open(os.path.join(Path(path).parent, path + "dw", file), 'w', encoding="utf-8") as wt:
            symbol, interval = file.split('-')[0], file.split('-')[1]
            print("ods-> dw  file:", file)
            try:
                rows = [
                    {
                        "timestamp": int(row['open_time']),
                        "symbol": symbol,
                        "open": Decimal(row['open']),
                        "high": Decimal(row['high']),
                        "low": Decimal(row['low']),
                        "close": Decimal(row['close']),
                        "volume": Decimal(row['volume']),
                        "amount": Decimal(row['quote_volume']),
                    }
                    for row in csv.DictReader(read)]
            except KeyError:
                rows = [
                    {
                        "timestamp": int(row['open_time']),
                        "symbol": symbol,
                        "open": Decimal(row['open']),
                        "high": Decimal(row['high']),
                        "low": Decimal(row['low']),
                        "close": Decimal(row['close']),
                        "volume": Decimal(row['volume']),
                        "amount": Decimal(row['quote_volume']),
                    } for row in csv.DictReader(read,
                                                fieldnames=["open_time", "open", "high", "low", "close", "volume",
                                                            "close_time",
                                                            "quote_volume", "count", "taker_buy_volume",
                                                            "taker_buy_quote_volume",
                                                            "ignore"])]
            writer = csv.DictWriter(wt, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    os.environ.setdefault("DISABLE_WORKER", "true")
    django.setup()
    __package__ = "workstation"

    parser = argparse.ArgumentParser(description='币安行情下在参数')

    # 定义期望接收的参数
    parser.add_argument('--pack', type=str, default="monthly")
    parser.add_argument('--start', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--end', type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument('--symbols', type=lambda x: x.split(','), default=[])
    parser.add_argument('--interval', type=lambda x: x.split(','), default=["1h", "4h", "6h", "8h", "12h", "1m", "3m", "5m", "15m", "30m", "1d"])
    parser.add_argument('--skip', type=int, default=0)
    args = parser.parse_args()
    print("    pack:", args.pack)
    print("   start:", args.start)
    print("     end:", args.end)
    print(" symbols:", args.symbols)
    print("interval:", args.interval)
    print("    skip:", args.skip)

    PACK_INTERVAL = args.pack  # daily/monthly
    download_binance_kline(args.start, args.end, symbols=args.symbols, intervals=args.interval, skip=args.skip)
    # python script_binance_data_download.py --pack=daily --start=2024-03-01 --end=2024-04-02 --interval=5m --skip=7
