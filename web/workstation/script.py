#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:26
# @Author  : shenglin.li
# @File    : script.py
# @Software: PyCharm
import csv
import sys
from decimal import Decimal
from pathlib import Path
import os

import django
import tqdm

root = Path(__file__).resolve().parent.parent.parent
if root in sys.path:
    sys.path.remove(f"{root}")
sys.path.append(f'{Path(__file__).resolve().parent.parent}')
sys.path.append(f'{root}')

from leek.common import IdGenerator

generator = IdGenerator(1)


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
    # for row in rows:
    #     print(row.to_dict())
    #     Kline.objects.bulk_create([row])


def deal_bian_download_csv():
    from leek.common import config
    all_files = sorted(os.listdir(config.DOWNLOAD_DIR))
    bar = tqdm.tqdm(all_files)
    for file in bar:
        bar.set_description("Deal %s" % file)
        # if file != "1000PEPEUSDT-15m-2023-06.csv":
        #     continue
        read_csv(config.DOWNLOAD_DIR, file)


def ods_2_dw():
    from leek.common import config
    all_files = os.listdir(config.DOWNLOAD_DIR)
    for file in all_files:
        with open(os.path.join(config.DOWNLOAD_DIR, file), 'r', encoding="utf-8") as read, \
                open(os.path.join(Path(config.DOWNLOAD_DIR).parent, "dw", file), 'w', encoding="utf-8") as wt:
            symbol, interval = file.split('-')[0], file.split('-')[1]
            print("file:", file)
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
    # ods_2_dw()
    deal_bian_download_csv()


