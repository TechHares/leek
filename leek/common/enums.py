#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/17 16:10
# @Author  : shenglin.li
# @File    : enums.py
# @Software: PyCharm
from enum import Enum


class KlineLevel(Enum):
    """
    K线级别
    """
    __milliseconds_map = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1H": 60 * 60 * 1000,
        "4H": 4 * 60 * 60 * 1000,
        "6H": 6 * 60 * 60 * 1000,
        "12H": 12 * 60 * 60 * 1000,
        "1D": 24 * 60 * 60 * 1000,
    }
    M1 = "1m"  # 一分钟
    M3 = "3m"  # 3分钟
    M5 = "5m"  # 5分钟
    M15 = "15m"
    M30 = "30m"
    H1 = "1H"  # 1小时
    H4 = "4H"  # 4小时
    H6 = "6H"  # 6小时
    H12 = "12H"  # 12小时
    D1 = "1D"  # 1天

    @property
    def milliseconds(self):
        return KlineLevel.__milliseconds_map[self.value]

if __name__ == '__main__':
    print(KlineLevel.H12.milliseconds)