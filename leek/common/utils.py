#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 10:57
# @Author  : shenglin.li
# @File    : utils.py
# @Software: PyCharm
import time
from decimal import *


def decimal_quantize(d, n=2, rounding=2):
    """
    decimal 精度处理
    :param d: 待处理decimal
    :param n: 小数位数
    :param rounding: 保留方式 0 四舍五入 1 进一法 2 舍弃
    :return:
    """
    if d is None:
        return None
    r = ROUND_HALF_DOWN
    if rounding == 1:
        r = ROUND_UP
    elif rounding == 2:
        r = ROUND_DOWN

    p = "0"
    if n > 0:
        p = "0." + "0" * n
    return d.quantize(Decimal(p), rounding=r)


def decimal_to_str(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class IdGenerator(object):
    def __init__(self, worker=1):
        self.worker = worker
        self.ts = 0
        self.idx = 0

    def next(self):
        ts = int(time.time())
        if ts != self.ts:
            self.ts = ts
            self.idx = 0
        else:
            self.idx += 1
        if self.idx > 999999:
            return self.next()
        return 1*(10**16) + self.ts * (10**6) + self.idx


if __name__ == '__main__':
    generator = IdGenerator(1)
    for i in range(10):
        print(generator.next())
