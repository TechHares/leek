#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/6 19:41
# @Author  : shenglin.li
# @File    : bias.py
# @Software: PyCharm
from leek.t.ma import MA
from leek.t.t import T


class BiasRatio(T):
    """
    乖离率
    """

    def __init__(self, window=10, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.ma = MA(window=window, max_cache=max_cache)

    def update(self, data):
        br = None
        try:
            ma = self.ma.update(data)
            if ma is None or ma == 0:
                return None
            br = (data.close - ma) / ma * 100
            return br
        finally:
            if data.finish == 1:
                self.cache.append(br)


if __name__ == '__main__':
    pass
