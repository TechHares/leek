#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/4 20:09
# @Author  : shenglin.li
# @File    : ma.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.common import G
from leek.t.t import T


class MA(T):
    def __init__(self, window=9, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, data):
        ma = None
        try:
            if len(self.q) < self.window - 1:
                return ma
            ls = list(self.q)
            ma = sum([d.close for d in ls], data.close) / self.window
            return ma
        finally:
            if data.finish == 1:
                self.q.append(data)
                self.cache.append(ma)


class EMA(T):
    def __init__(self, window=9, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.pre_ma = None
        self.alpha = Decimal(2 / (self.window + 1))

    def update(self, data):
        ma = None
        try:
            if self.pre_ma is None:
                ma = data.close
                return ma
            ma = self.alpha * data.close + (1 - self.alpha) * self.pre_ma
            return ma
        finally:
            if data.finish == 1:
                self.pre_ma = ma
                self.cache.append(ma)


if __name__ == '__main__':
    pass
