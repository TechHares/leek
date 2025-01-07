#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/4 20:09
# @Author  : shenglin.li
# @File    : ma.py
# @Software: PyCharm
import math
from collections import deque
from decimal import Decimal
from functools import reduce

import numpy as np

from leek.t.t import T


class WR(T):
    """
    拉里·威廉斯指数（简称威廉指标）
    威廉指标与随机指数的概念类似，也表示当日的收市价格在过去一定天数里的全部价格范围中的相对位置。威廉指标的刻度与随机指数的刻度比起来，
    顺序正好相反， 0 到 20 算作超买区， 80 到 100 为超卖区。
    """

    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, data):
        wr = None
        try:
            if len(self.q) < self.window - 1:
                return wr
            ls = list(self.q)
            ls.append(data)
            high = max([x.high for x in ls])
            low = min([x.low for x in ls])
            if high == low:
                wr = 100
            else:
                wr = float(100 * (high - data.close) / (high - low))
            return wr
        finally:
            if data.finish == 1:
                self.q.append(data)
                self.cache.append(wr)

if __name__ == '__main__':
    pass
