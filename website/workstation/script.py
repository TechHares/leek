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


def read_csv(file_dir, file):
    from .models import Kline
    symbol, interval = file.split('-')[0], file.split('-')[1]
    print("file:", file)
    try:
        rows = [Kline(
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
    # Kline.objects.using(interval).bulk_create(rows, ignore_conflicts=True)
    print(len(rows))


def deal_bian_download_csv():
    from leek.common import config
    all_files = os.listdir(config.DOWNLOAD_DIR)
    for file in all_files:
        read_csv(config.DOWNLOAD_DIR, file)


if __name__ == '__main__':
    __package__ = "workstation"
    sys.path.append(f'{Path(__file__).resolve().parent.parent.parent}/website')
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    os.environ.setdefault("DISABLE_WORKER", "true")
    django.setup()
    deal_bian_download_csv()
