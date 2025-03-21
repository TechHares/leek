#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:57
# @Author  : shenglin.li
# @File    : t.py
# @Software: PyCharm
import abc
from abc import abstractmethod
from collections import deque

from leek.common import G


class T(metaclass=abc.ABCMeta):
    def __init__(self, max_cache=100):
        self.cache = deque(maxlen=max_cache)

    @abstractmethod
    def update(self, data):
        pass

    def last(self, n=100):
        n = min(len(self.cache), n)
        return list(self.cache)[-n:]


class MERGE(T):
    """
    K线合并(周期升级)
    """
    _CONFIG_INTERVAL = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "6h": 6 * 60 * 60 * 1000,
        "12h": 12 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }
    def __init__(self, window=9, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window)

        self.not_start = True

    def update(self, data):
        if self.not_start:
            if  data.timestamp % int(self.window * self._CONFIG_INTERVAL[data.interval]) != 0:
                return None
            self.not_start = False

        if len(self.q) > 0 and self.q[-1].finish == 0:
            self.q.pop()

        self.q.append(data)
        ls = list(self.q)
        r = G(symbol=data.symbol,
              interval=f"{data.interval}({self.window})",
              timestamp=ls[0].timestamp,
              current_time=data.current_time,
              open=ls[0].open,
              high=max(d.high for d in ls),
              low=min(d.low for d in ls),
              close=data.close,
              volume=sum(d.volume for d in ls),
              amount=sum(d.amount for d in ls),
              finish=0
              )
        if len(ls) == self.window and data.finish == 1:
            r.finish = 1
            self.q.clear()
            self.cache.append(r)

        return r

if __name__ == '__main__':
    pass
