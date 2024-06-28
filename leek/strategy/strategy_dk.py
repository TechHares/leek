#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/27 19:49
# @Author  : shenglin.li
# @File    : strategy_dk.py
# @Software: PyCharm
from leek.strategy import BaseStrategy
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.t import DK, LLT, MA
from leek.trade.trade import PositionSide


class DKStrategy(DynamicRiskControl, PositionRateManager, BaseStrategy):
    verbose_name = "DK(模拟指标)"

    def __init__(self):
        self.dk = DK(MA)

    def handle(self):
        dk = self.dk.update(self.market_data)
        self.market_data.dk = dk
        if self.have_position():
            if not dk:
                self.close_position("DK空头")
        else:
            if dk:
                self.create_order(PositionSide.LONG, self.max_single_position)


if __name__ == '__main__':
    pass
