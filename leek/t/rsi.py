#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/18 20:48
# @Author  : shenglin.li
# @File    : kdj.py
# @Software: PyCharm
from collections import deque

from leek.common import G, logger
from leek.t.t import T


class RSI(T):
    """
    相对强弱指数
    """

    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max(max_cache, max_cache))
        self.window = window
        self.q = deque(maxlen=window)

        self.pre_gain = None  # 增益
        self.pre_loss = None  # 损失

    def update(self, data):
        rsi = None
        pre_gain = self.pre_gain
        pre_loss = self.pre_loss
        try:
            data.delta = 0
            if len(self.q) > 0:
                data.delta = float(data.close) - float(list(self.q)[-1].close)
            if len(self.q) < self.window:
                return rsi

            if pre_gain is None:
                ls = [data.delta for data in list(self.q)[-self.window + 1:]]
                ls.append(data.delta)
                pre_gain = sum([x for x in ls if x > 0]) / self.window
                pre_loss = -sum([x for x in ls if x < 0]) / self.window
            else:
                pre_gain = (pre_gain / self.window * (self.window - 1)) + max(data.delta, 0) / self.window
                pre_loss = (pre_loss / self.window * (self.window - 1)) - min(0, data.delta) / self.window
            rsi = 0.0
            # 计算平滑增益和损失
            if pre_gain+pre_loss != 0:
                rsi = pre_gain/(pre_gain+pre_loss) * 100
            logger.info(f"RSI计算[{self.window}]：pre_gain:{pre_gain}, pre_loss:{pre_loss}, delta:{data.delta} => rsi:{rsi}")
            return rsi
        finally:
            if data.finish == 1:
                self.q.append(data)
                self.pre_gain = pre_gain
                self.pre_loss = pre_loss
                if rsi:
                    self.cache.append(rsi)


class StochRSI(T):
    """
    随机相对强弱指数
    """
    def __init__(self, window=14, period=14, k_smoothing_factor=3, d_smoothing_factor=3, max_cache=100):
        T.__init__(self, max(window, period, max_cache))
        self.period = period
        self.k_smoothing_factor = k_smoothing_factor
        self.d_smoothing_factor = d_smoothing_factor
        self.rsi = RSI(window, k_smoothing_factor + period + 1)

    def update(self, data):
        stoch_rsi = [None, None]
        try:
            rsi = self.rsi.update(data)
            if rsi is None:
                return stoch_rsi
            last = self.rsi.last(self.k_smoothing_factor + self.period)
            if len(last) < self.k_smoothing_factor + self.period:
                return stoch_rsi
            if data.finish == 0:
                last.append(rsi)

            num = []
            devno = []
            logger.debug(f"RSI:{last}, {rsi}, => {data.finish}")
            for i in range(self.k_smoothing_factor, 0, -1):
                d = last[-i - self.period:-i]
                num.append(d[-1] - min(d))
                devno.append(max(d) - min(d))
            stoch_rsi[0] = 100
            if sum(devno) != 0:
                stoch_rsi[0] = sum(num) / sum(devno) * 100

            c = list(self.cache)
            logger.debug(f"STOCH RSI:{self.last(10)}, {stoch_rsi[0]}")
            if data.finish != 1:
                c.append(stoch_rsi)
            if len(c) > self.d_smoothing_factor and c[-self.d_smoothing_factor+1][0] is not None:
                stoch_rsi[1] = (sum([x[0] for x in c[-self.d_smoothing_factor+1:]]) + stoch_rsi[0]) / self.d_smoothing_factor
            return stoch_rsi
        finally:
            if data.finish == 1 and stoch_rsi[0]:
                self.cache.append(stoch_rsi)


if __name__ == '__main__':
    pass
