#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/29 15:52
# @Author  : shenglin.li
# @File    : calculator.py
# @Software: PyCharm
from decimal import Decimal
from collections import deque

import numpy as np
import pandas as pd


class Calculator(object):
    def __init__(self, max_size=100):
        self.max_size = max_size
        self.q = deque(maxlen=max_size)

    def add_element(self, element):
        if len(self.q) > 0 and self.q[-1].timestamp == element.timestamp:
            return
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
            alpha = Decimal(2 / (window + 1))

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

    def stochastics(self, k_period=14, d_period=3, smooth=1):
        if len(self.q) < (k_period + d_period + smooth - 1):
            return 0, 0, 0
        data = list(self.q)
        df = pd.DataFrame([d.__json__() for d in data])
        # 计算14日内的最高价和最低价
        df['rolling-high'] = df['high'].rolling(k_period).max().apply(lambda x: Decimal(x))
        df['rolling-low'] = df['low'].rolling(k_period).min().apply(lambda x: Decimal(x))

        # 计算 %K 值
        df['%K'] = (100 * (df['close'] - df['rolling-low']) / (df['rolling-high'] - df['rolling-low'])).apply(
            lambda x: x.__float__())

        # 计算 %D 值
        df['%D'] = df['%K'].rolling(d_period).mean()
        # 计算 %D_smooth 值
        df['%D_smooth'] = df['%D'].rolling(smooth).mean()

        return df

    def atr(self, n=3, window=14):
        if len(self.q) < window + n - 1:
            return None

        data = list(self.q)
        df = pd.DataFrame([d.__json__() for d in data])
        # 计算 ATR
        df['TR'] = df['high'] - df['low']
        df['TR1'] = abs(df['high'] - df['close'].shift(1))
        df['TR2'] = abs(df['low'] - df['close'].shift(1))
        df['TR'] = df[['TR', 'TR1', 'TR2']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=window).mean()

        return df.tail(n)["ATR"].tolist()

    def heikin_ashi(self):
        """
        判断趋势开始 连续三个颜色一致，且往前第四个不一样
        :return: df k线数据
        """
        if len(self.q) < 5:
            return None

        data = list(self.q)
        df = pd.DataFrame([d.__json__() for d in data])
        # 计算 Heikin-Ashi
        df["ha_close"] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        df["ha_open"] = (df['open'].shift(1) + df['close'].shift(1)) / 2
        df["ha_high"] = df[['high', 'open', 'close']].max(axis=1)
        df["ha_low"] = df[['low', 'open', 'close']].min(axis=1)

        df['side'] = 1
        df.loc[df['ha_close'] < df['ha_open'], 'side'] = 2
        return df

    def ama(self, period=9, slow_coefficient=30, fast_coefficient=2):
        if len(self.q) < period + 1:
            return None

        data = list(self.q)
        df = pd.DataFrame([d.__json__() for d in data])

        df['change_value'] = (df["close"] - df["close"].shift(period)).abs()
        df['volatility_value'] = df["close"].diff(period).abs().sum()
        df['er'] = (df['change_value'] / df['volatility_value'])
        fast_sc = Decimal(2 / (fast_coefficient + 1))
        slow_sc = Decimal(2 / (slow_coefficient + 1))
        df['ssc'] = (df['er'] * (fast_sc - slow_sc) + slow_sc) * 2

        df['ama'] = df['close'].copy()
        for i in range(period, len(df)):
            df.loc[i, 'ama'] = df.loc[i - 1, 'ama'] + (df.loc[i, 'ssc'] * (df.loc[i, 'close'] - df.loc[i - 1, 'ama']))
        return df.tail(period)["ama"].tolist()


if __name__ == '__main__':
    # pass
    import pandas as pd

    s = pd.Series([1, 2, 3, 4, 5])
    result = s.diff(periods=3)
    print(result)
