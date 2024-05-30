#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:45
# @Author  : shenglin.li
# @File    : sar.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.t.t import T


class SAR(T):
    def __init__(self, initial_af="0.02", af_max="0.2", step_increment="0.02", max_cache=10):
        T.__init__(self, max_cache=max_cache)
        self.initial_af = Decimal(initial_af)
        self.af_max = Decimal(af_max)
        self.step_increment = Decimal(step_increment)

        self.af = Decimal(self.initial_af)
        self.sar = None
        self.ep = None
        self.is_long = True

    def update(self, data):
        try:
            if self.sar is None:
                self.sar = data.low
                self.ep = data.high
                return self.sar, self.is_long
            self.sar = self.sar + self.af * (self.ep - self.sar)
            if self.is_long:
                self.ep = max(data.high, self.ep)
                if data.close < self.sar:
                    self.is_long = False
                    self.sar = data.high
                    self.af = self.initial_af
            else:
                self.ep = min(data.low, self.ep)
                if data.close > self.sar:
                    self.is_long = True
                    self.sar = data.low
                    self.af = self.initial_af
            self.af = min(self.af + self.step_increment, self.af_max)
            return self.sar, self.is_long
        finally:
            if data.finish == 1:
                self.cache.append(self.sar)


if __name__ == '__main__':
    pass

