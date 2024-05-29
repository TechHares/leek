#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:48
# @Author  : shenglin.li
# @File    : atr.py
# @Software: PyCharm
from collections import deque

from leek.common import G
from leek.t.t import T


class ATR(T):
    """
    真实波动率
    """

    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)
        self.pre_close = None

    def update(self, data):
        tr = data.high - data.low
        atr = None
        try:
            ls = list(self.q)
            if len(ls) > 0:
                tr = max(tr, abs(data.high - self.pre_close), abs(data.low - self.pre_close))
            atr = (sum([d.tr for d in ls]) + tr) / (len(ls) + 1)
            return atr
        finally:
            if data.finish == 1:
                self.q.append(G(tr=tr, atr=atr))
                self.pre_close = data.close
                self.cache.append(atr)


if __name__ == '__main__':
    pass
