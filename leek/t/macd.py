#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/10 19:45
# @Author  : shenglin.li
# @File    : sar.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.common import G
from leek.t import MA, EMA
from leek.t.t import T


class MACD(T):

    def __init__(self, fast_period=12, slow_period=26, moving_period=9, max_cache=10):
        T.__init__(self, max_cache=max_cache)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.moving_period = moving_period

        self.fast_ma = EMA(self.fast_period)
        self.slow_ma = EMA(self.slow_period)
        self.dea = EMA(self.moving_period)

    def update(self, data):
        fast = self.fast_ma.update(data)
        slow = self.slow_ma.update(data)
        if slow is None or fast is None:
            return None, None
        dif = fast - slow
        g = G(close=dif, finish=data.finish)
        dea = self.dea.update(g)
        if dea is None:
            return dif, None
        if data.finish == 1:
            self.cache.append((dif, dea))
        return dif, dea



if __name__ == '__main__':
    pass

