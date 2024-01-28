#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/27 21:53
# @Author  : shenglin.li
# @File    : strategy_bollinger_bands.py
# @Software: PyCharm
from leek.common import G
from leek.strategy import BaseStrategy
from leek.trade.trade import Order


class BollingerBandsStrategy(BaseStrategy):
    """
    布林带策略
    核心思想：利用统计原理，求出股价的标准差及其信赖区间，从而确定股价的波动范围及未来走势，利用波带显示股价的安全高低价位
    风险: 单边行情
    """
    def __init__(self):
        pass

    def handle(self, market_data: G) -> Order:
        pass

    def calculate_bollinger_bands(self, prices, window=20, num_std_dev=2):
        # 计算移动平均
        rolling_mean = prices.rolling(window=window).mean()

        # 计算标准差
        rolling_std = prices.rolling(window=window).std()

        # 计算上轨和下轨
        upper_band = rolling_mean + (rolling_std * num_std_dev)
        lower_band = rolling_mean - (rolling_std * num_std_dev)

        return rolling_mean, upper_band, lower_band


if __name__ == '__main__':
    pass
