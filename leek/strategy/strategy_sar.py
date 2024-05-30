#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/20 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
from collections import deque

from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import SAR
from leek.trade.trade import PositionSide


class SARStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "SAR短线择时"

    def __init__(self, fast_period=5, slow_period=5):
        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.sar = SAR()

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(maxlen=self.fast_period + self.slow_period)

        sar, is_long = self.sar.update(self.market_data)
        self.market_data.sar = sar
        return is_long

    def handle(self):
        """
            n1 次同方向 进入确认阶段， 发生反转金额确认阶段， n2 次之内再反转， 开仓， 再反转平仓
        """
        is_long = self._calculate()
        try:
            if self.have_position():
                if self.is_long_position() and not is_long:
                    self.close_position("空翻多")
                if self.is_short_position() and is_long:
                    self.close_position("多翻空")
                return

            if not self.enough_amount():
                return

            if is_long and self.can_long() and self.check_sar_series(list(self.g.q), is_long):
                self.create_order(PositionSide.LONG, self.max_single_position)

            if not is_long and self.can_short() and self.check_sar_series(list(self.g.q), is_long):
                self.create_order(PositionSide.SHORT, self.max_single_position)
        finally:
            if self.market_data.finish == 1:
                self.g.q.append(is_long)

    def check_sar_series(self, data, target):
        if len(data) < self.fast_period + self.slow_period:
            return False

        rev = True
        ct = 0
        for i in range(1, len(data) + 1):
            if rev:
                if data[-i] != target:
                    ct += 1
                    if ct > self.slow_period:
                        return False
                else:
                    if ct == 0:
                        return False
                    if ct <= self.slow_period:
                        rev = False
                        ct = 0
            else:
                if data[-i] == target:
                    ct += 1
                else:
                    break
        return ct >= self.fast_period


if __name__ == '__main__':
    pass
