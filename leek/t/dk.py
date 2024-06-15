#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/14 20:09
# @Author  : shenglin.li
# @File    : ma.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.common import G
from leek.t.ma import MA, LLT
from leek.t.t import T


class DK(T):
    """
    仅多
    """
    def __init__(self, ma_type=MA, max_cache=1000):
        T.__init__(self, max_cache)
        self.ma5 = ma_type(5, max_cache)
        self.ma10 = ma_type(10, max_cache)
        self.ma20 = ma_type(20, max_cache)

    def update(self, data):
        rc = False
        try:
            ma5 = self.ma5.update(data)

            pre_ma10 = self.ma10.last(1)
            if len(pre_ma10) == 0:
                pre_ma10 = [10000000]
            pre_ma10 = pre_ma10[0]
            ma10 = self.ma10.update(data)

            pre_ma20 = self.ma20.last(1)
            if len(pre_ma20) == 0:
                pre_ma20 = [10000000]
            ma20 = self.ma20.update(data)
            pre_ma20 = pre_ma20[0]
            rc = (ma5 and ma10 and ma20 and pre_ma20 and pre_ma10) and (ma5 >= ma20 or pre_ma20 <= ma20) \
                and (ma5 >= ma10 or pre_ma10 / ma10 >= Decimal("0.01")) and (pre_ma20 <= ma20)

            return rc
        finally:
            if data.finish == 1:
                self.cache.append(rc)


if __name__ == '__main__':
    pass
