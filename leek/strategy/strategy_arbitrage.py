#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 22:09
# @Author  : shenglin.li
# @File    : strategy_arbitrage.py
# @Software: PyCharm
from okx import MarketData
from okx.PublicData import PublicAPI

from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager


class FundingStrategy(PositionRateManager, BaseStrategy):
    verbose_name = "资金费套利"

    def __init__(self):
        pass

    def handle(self):
        print(self.market_data)


if __name__ == '__main__':
    pass
