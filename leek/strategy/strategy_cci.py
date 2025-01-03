#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/27 21:49
# @Author  : shenglin.li
# @File    : strategy_cci.py
# @Software: PyCharm
"""

"""
from leek.strategy import BaseStrategy
from leek.strategy.base import Position
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import MA, CCI, CCIV2
from leek.trade.trade import PositionSide


class CCIStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "CCI简单应用"

    def __init__(self, window=12, fast_period=5, slow_period=20, over_sell=-100, over_buy=100):

        self.fast_ma = MA(int(fast_period))
        self.slow_ma = MA(int(slow_period))
        self.cci = CCI(int(window))
        # self.cci = CCIV2(int(window))

        self.over_sell = int(over_sell)
        self.over_buy = int(over_buy)

    def _calculate(self, data):
        data.fast_ma = self.fast_ma.update(data)
        data.slow_ma = self.slow_ma.update(data)
        last = self.cci.last(1)
        if len(last) > 0:
            data.pre_cci = last[-1]
        data.cci = self.cci.update(data)

    def handle(self):
        k = self.market_data
        self._calculate(k)
        if k.fast_ma is None or k.slow_ma is None or k.cci is None or k.pre_cci is None:
            return

        if self.have_position():
            if self.is_long_position():  # 多
                if k.fast_ma < k.slow_ma or k.cci < 0:
                    self.close_position()
            else:
                if k.fast_ma > k.slow_ma or k.cci > 0:
                    self.close_position()
        else:
            if k.fast_ma > k.slow_ma and self.can_long():  # 多
                if k.cci > self.over_buy > k.pre_cci:
                    self.create_order(PositionSide.LONG, self.max_single_position)
            if k.fast_ma < k.slow_ma and self.can_short():  # 空
                if k.cci < self.over_sell < k.pre_cci:
                    self.create_order(PositionSide.SHORT, self.max_single_position)

if __name__ == '__main__':
    pass
