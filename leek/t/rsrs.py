#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 17:31
# @Author  : shenglin.li
# @File    : rsrs.py
# @Software: PyCharm
from collections import deque

import numpy as np

from leek.t.t import T
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


class RSRS(T):
    def __init__(self, window=18, static_window=600, max_cache=10):
        T.__init__(self, max_cache=max(max_cache, static_window))
        self.n = window - 1
        self.static_window = static_window
        self.high_prices = deque(maxlen=self.n)
        self.low_prices = deque(maxlen=self.n)

    def update(self, data):
        beta = None
        try:
            if len(self.low_prices) < self.n:
                return beta, None, None, None
            high_series = list(self.high_prices)
            high_series.append(data.high)
            low_series = list(self.low_prices)
            low_series.append(data.low)

            x = np.array(low_series).reshape(-1, 1)
            y = np.array(high_series)
            model = LinearRegression()
            model.fit(x, y)
            beta = model.coef_[0]
            y_pred = model.predict(x.reshape(-1, 1))
            r2 = r2_score(y, y_pred)
            std_score = None
            mdf_std_score = None
            rsk_std_score = None
            if len(self.cache) >= self.static_window:
                betas = np.array(list(self.cache)[-self.static_window:])
                std_score = (beta - betas.mean()) / betas.std()
                mdf_std_score = std_score * r2
                rsk_std_score = mdf_std_score * beta
            return beta, std_score, mdf_std_score, rsk_std_score
        finally:
            if data.finish == 1:
                self.low_prices.append(data.low)
                self.high_prices.append(data.high)
                if beta:
                    self.cache.append(beta)


if __name__ == '__main__':
    from leek.common import G
    rsrs = RSRS(window=3)
    data = [G(high=21, low=1, close=11), G(high=22, low=2, close=12), G(high=23, low=3, close=13),
            G(high=24, low=4, close=14), G(high=25, low=5, close=15), G(high=26, low=6, close=16),
            G(high=27, low=7, close=17), G(high=28, low=8, close=18), G(high=29, low=9, close=19),
            G(high=210, low=10, close=110), ]
    for d in data:
        d.finish = 1
        rsrs.update(d)
