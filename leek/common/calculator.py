#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/29 15:52
# @Author  : shenglin.li
# @File    : calculator.py
# @Software: PyCharm
import decimal
from collections import deque

import numpy as np


class Calculator(object):
    def __init__(self, max_size=100):
        self.max_size = max_size
        self.q = deque(maxlen=max_size)

    def add_element(self, element):
        self.q.append(element)

    def get_elements(self, window=None):
        if window is None or window == self.max_size:
            return list(self.q)
        return list(self.q)[-window]

    def sma(self, window=None, new_price=None):
        if len(self.q) < window:
            return 0
        if window is None:
            window = self.max_size
        if new_price is None:
            return np.mean([x.close for x in self.get_elements(window)])
        _window = [x.close for x in self.get_elements(window - 1)]
        _window.append(new_price)
        return np.mean(_window)

    def ema(self, close=None, window=None, alpha=None):
        if window is None:
            window = self.max_size
        if len(self.q) < window:
            return 0
        if alpha is None:
            alpha = decimal.Decimal(2 / (window + 1))

        ema = self.q[0].close
        for i in range(1, len(self.q)):
            ema = alpha * (self.q[i].close - ema) + ema
        return ema if close is None else alpha * (close - ema) + ema

    def boll(self, new_price=None, window=None, num_std_dev=2):
        if window is None:
            window = self.max_size
        if len(self.q) < window:
            return 0, 0, 0
        rolling_mean = self.sma(new_price=new_price, window=window)
        rolling_std = np.std([x.close for x in self.get_elements(window)])
        # 计算上轨和下轨
        upper_band = rolling_mean + (rolling_std * num_std_dev)
        lower_band = rolling_mean - (rolling_std * num_std_dev)

        return upper_band, rolling_mean, lower_band


if __name__ == '__main__':
    pass
