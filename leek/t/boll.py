#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/4 20:18
# @Author  : shenglin.li
# @File    : boll.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import numpy as np

from leek.t.t import T
from leek.t.ma import MA


class BollBand(T):

    def __init__(self, window=20, num_std_dev=2, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.num_std_dev = Decimal(num_std_dev)
        self.q = deque(maxlen=window - 1)
        self.ma = MA(window)

    def update(self, data):
        boll_band = None
        try:
            middle = self.ma.update(data)
            if not middle:
                return boll_band

            ls = list(self.q)
            ls.append(data.close)
            std = np.std(ls)
            upper_band = middle + (std * self.num_std_dev)
            lower_band = middle - (std * self.num_std_dev)
            boll_band = (lower_band, middle, upper_band)
            return boll_band
        finally:
            if data.finish == 1:
                self.q.append(data.close)
                self.cache.append(boll_band)


if __name__ == '__main__':
    pass
