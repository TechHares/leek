#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/11 20:03
# @Author  : shenglin.li
# @File    : strategy_super_trend.py
# @Software: PyCharm
from leek.strategy import BaseStrategy
from leek.strategy.common.decision import STDecisionNode
from leek.strategy.common.strategy_common import PositionRateManager
from leek.trade.trade import PositionSide


class SuperTrendStrategy(PositionRateManager, BaseStrategy):
    verbose_name = "超级趋势"

    def __init__(self, smoothing_period=10, factory=3):
        self.period = int(smoothing_period)
        self.factory = int(factory)
        self.evaluation_data = []

    def handle(self):
        if self.market_data.finish != 1:
            return

        if self.g.node is None:
            self.g.node = STDecisionNode(self.period, self.factory)

        if self.have_position():
            if self.g.node.close_long(self.market_data):
                self.close_position()
        else:
            if not self.enough_amount():
                return 
            if self.g.node.open_long(self.market_data):
                self.create_order(PositionSide.LONG, self.max_single_position)


if __name__ == '__main__':
    pass
