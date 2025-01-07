#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/30 21:19
# @Author  : shenglin.li
# @File    : cci.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.t.ma import MA
from leek.t.t import T


class CCI(T):
    """
    CCI（Commodity Channel Index，商品通道指数）是一个技术分析指标，由Donald Lambert在1980年提出。
    CCI用来衡量一个资产价格相对于其统计平均价格的偏离程度，常用于识别资产价格是否处于超买或超卖状态
    |cci| > 100 认为出现超买超卖
    """

    def __init__(self, window=12, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.ma = MA(window=12, vfunc=lambda x: x)
        self.q = deque(maxlen=window-1)

    def update(self, data):
        cci = None
        tp = (data.high + data.low + data.close) / 3
        try:
            tp_ma = self.ma.update(tp, data.finish == 1)

            if tp_ma is None:
                return cci

            ls = list(self.q)
            ls.append(tp)
            if len(ls) < self.window:
                return cci
            md = sum([abs(x - tp_ma) for x in ls]) / self.window
            cci = (tp - tp_ma) / (Decimal("0.015") * md)

            return cci
        finally:
            if data.finish == 1:
                self.cache.append(cci)
                self.q.append(tp)

class CCIV2(T):
    """
    这个版本MD计算更均衡的SMA
    """

    def __init__(self, window=12, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.ma = MA(window=12, vfunc=lambda x: x)
        self.md_ma = MA(window=12, vfunc=lambda x: x)
        self.q = deque(maxlen=window-1)

    def update(self, data):
        cci = None
        tp = (data.high + data.low + data.close) / 3
        try:
            tp_ma = self.ma.update(tp, data.finish == 1)
            if tp_ma is None:
                return cci

            md = self.md_ma.update(abs(tp - tp_ma), data.finish == 1)
            if md is None:
                return cci
            cci = (tp - tp_ma) / (Decimal("0.015") * md)
            return cci
        finally:
            if data.finish == 1:
                self.cache.append(cci)
                self.q.append(tp)


if __name__ == '__main__':
    pass
