#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/17 20:49
# @Author  : shenglin.li
# @File    : strategy_htm.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import numpy as np

from leek.strategy import BaseStrategy
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import LLT, FRAMA, MA
from leek.trade.trade import PositionSide
from scipy.signal import hilbert


class HTMStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "希尔伯特变换择时"
    """
    参考资料：
        广发证券《短线择时策略研究之二——希尔伯特变换下的短线择时策略》
    """

    def __init__(self):
        self.ma = MA(20)
        self.hilbert_window = deque(maxlen=100)

        self.pre = None

    def _calculate(self):
        # 使用均线过滤噪声
        try:
            self.market_data.ma = self.ma.update(self.market_data)
            p = [d for d in list(self.hilbert_window)]
            price = self.market_data.close
            self.market_data.s = 0
            self.market_data.d = 0
            self.market_data.q = 0
            self.market_data.i = 0
            if len(p) >= 3:
                self.market_data.s = (4 * price + 3 * p[-1].close + 2 * p[-2].close + p[-3].close) / 10

            f1 = Decimal("0.25")
            f2 = Decimal("0.75")
            if len(p) >= 6:
                self.market_data.d = (f1 * self.market_data.s + f2 * p[-2].s - f1 * p[-4].s - f2 * p[-6].s)
                self.market_data.r = (f1 * self.market_data.d + f2 * p[-2].d - f1 * p[-4].d - f2 * p[-6].d)

            if len(p) >= 9:
                self.market_data.i = p[-3].d
        finally:
            if self.market_data.finish == 1:
                self.hilbert_window.append(self.market_data)

    # 转换2
    # def _calculate(self):
    #     # 使用均线过滤噪声
    #     pre = self.pre
    #     if self.market_data.finish == 1:
    #         self.pre = self.market_data
    #         self.hilbert_window.append(self.market_data)
    #     self.market_data.ma = self.ma.update(self.market_data)
    #     if self.market_data.ma is None:
    #         return
    #     if pre is None or pre.ma is None:
    #         return
    #
    #     # 差分
    #     self.market_data.dsr = self.market_data.ma - pre.ma
    #     if len(self.hilbert_window) < self.hilbert_window.maxlen:
    #         return
    #     dsr_list = [d.dsr for d in list(self.hilbert_window)]
    #     if self.market_data.finish != 1:
    #         dsr_list = dsr_list[1:]
    #         dsr_list.append(self.market_data.dsr)
    #     xh = hilbert(dsr_list)
    #     self.market_data.r = np.real(xh)[-1]
    #     self.market_data.i = np.imag(xh)[-1]

    def handle(self):
        """
        二四象限空仓
        进入第一象限买入，出第一四象限卖出
        进入第三象限做空，出第二三象限平仓
        """
        self._calculate()
        if self.market_data.r is None or self.market_data.i is None:
            return
        if self.have_position():
            if self.is_long_position() and self.market_data.i < 0:
                self.close_position(memo="平多")
            if self.is_short_position() and not self.market_data.i > 0:
                self.close_position(memo="平空")
        else:
            if self.can_long() and self.market_data.r > 0 and self.market_data.i > 0:
                self.create_order(PositionSide.LONG)
            if self.can_short() and self.market_data.r < 0 and self.market_data.i < 0:
                self.create_order(PositionSide.SHORT)


if __name__ == '__main__':
    pass
