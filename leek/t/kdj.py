#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/03 20:48
# @Author  : shenglin.li
# @File    : kdj.py
# @Software: PyCharm
from collections import deque

from leek.common import G
from leek.t.t import T


class KDJ(T):

    def __init__(self, window=9, k_smoothing_factor=3, d_smoothing_factor=3, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.k_smoothing_factor = k_smoothing_factor
        self.d_smoothing_factor = d_smoothing_factor
        self.q = deque(maxlen=window - 1)

    def update(self, data):
        kdj = None
        try:
            if len(self.q) < self.window - 1:
                return kdj
            ls = list(self.q)
            max_price = max(max(ls, key=lambda x: x.high).high, data.high)
            min_price = min(min(ls, key=lambda x: x.low).low, data.low)
            rsv = 0
            if max_price != min_price:
                rsv = (data.close - min_price) / (max_price - min_price) * 100

            pre_k = rsv
            last = self.last(1)
            if last and last[0]:
                pre_k = last[0][0]
            k = (pre_k * (self.k_smoothing_factor - 1) + rsv) / self.k_smoothing_factor

            pre_d = k
            last = self.last(1)
            if last and last[0]:
                pre_d = last[0][1]
            d = (pre_d * (self.d_smoothing_factor - 1) + k) / self.d_smoothing_factor

            j = 3 * k - 2 * d
            kdj = (k, d, j)
            return kdj
        finally:
            if data.finish == 1:
                self.q.append(data)
                self.cache.append(kdj)


if __name__ == '__main__':
    pass
