#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/17 20:48
# @Author  : shenglin.li
# @File    : dsp.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import numpy as np

from leek.common import G, logger
from leek.t.ma import SuperSmoother
from leek.t.t import T
"""
数字信号处理指标(DSP)
"""

class Reflex(T):
    """
    反曲弓 《Technical Analysis of Stocks and Commodities》，业内简称“S&C”）上，约翰•埃勒斯（John F. Ehlers）在2020年2月刊文章《Reflex: A New Zero-Lag Indicator》
    """

    def __init__(self, window=20, max_cache=100):
        T.__init__(self, max(window, max_cache))
        self.window = window
        self.smoother = SuperSmoother(window // 2)

        self.pre_ms = None

    def update(self, data):
        reflex = None
        try:
            update = self.smoother.update(data)
            filt = self.smoother.last(self.window)
            if data.finish == 0:
                filt.append(update)
                filt = filt[1:]
            if len(filt) < self.window:
                return reflex

            slope = (filt[0] - filt[-1]) / self.window
            # y = kx + b;  k=slope, b=filt[0]
            sum_diff = 0
            for i in range(0, len(filt)):
                # y' = slope * i + filt[0]
                # s = y' - y
                sum_diff += (filt[-1] + i * slope) - filt[i]
            sum_diff /= len(filt)

            if self.pre_ms is None:
                ms = sum_diff ** 2
            else:
                ms = Decimal("0.04") * (sum_diff ** 2) + Decimal("0.96") * self.pre_ms
            if data.finish == 1:
                self.pre_ms = ms

            if ms != 0:
                reflex = sum_diff / np.sqrt(ms)
            else:
                reflex = 0

            return reflex
        finally:
            if data.finish == 1 and reflex:
                self.cache.append(reflex)

class TrendFlex(T):
    """
    《Technical Analysis of Stocks and Commodities》，业内简称“S&C”）上，约翰•埃勒斯（John F. Ehlers）在2020年2月刊文章《Reflex: A New Zero-Lag Indicator》
    """

    def __init__(self, window=20, max_cache=100):
        T.__init__(self, max(window, max_cache))
        self.window = window
        self.smoother = SuperSmoother(window // 2)

        self.pre_ms = None

    def update(self, data):
        trend_flex = None
        try:
            update = self.smoother.update(data)
            filt = self.smoother.last(self.window)
            if data.finish == 0:
                filt.append(update)
                filt = filt[1:]
            if len(filt) < self.window:
                return trend_flex

            sum_diff = 0
            for i in range(0, len(filt)):
                sum_diff += filt[-1] - filt[i]
            sum_diff /= len(filt)

            if self.pre_ms is None:
                ms = sum_diff ** 2
            else:
                ms = Decimal("0.04") * (sum_diff ** 2) + Decimal("0.96") * self.pre_ms
            if data.finish == 1:
                self.pre_ms = ms

            if ms != 0:
                trend_flex = sum_diff / np.sqrt(ms)
            else:
                trend_flex = 0

            return trend_flex
        finally:
            if data.finish == 1 and trend_flex:
                self.cache.append(trend_flex)



if __name__ == '__main__':
    pass
