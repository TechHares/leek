#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/3/18 15:19
# @Author  : shenglin.li
# @File    : strategy_macd.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import cachetools

from leek.common import G
from leek.strategy import *
from leek.strategy.common import Calculator
from leek.strategy.common.strategy_common import PositionRateManager, CalculatorContainer, PositionDirectionManager
from leek.trade.trade import PositionSide


class SingleMaStrategy(PositionRateManager, CalculatorContainer, BaseStrategy):
    verbose_name = "单均线策略"

    def __init__(self, mean_type="sma"):
        self.mean_type = mean_type

    def calculator(self, market_data: G) -> Calculator:
        if market_data.symbol not in self.window_container:
            self.window_container[market_data.symbol] = Calculator(self.window * 2)
        if market_data.finish == 1:
            self.window_container[market_data.symbol].add_element(market_data)
        return self.window_container[market_data.symbol]

    def handle(self):
        if self.market_data.finish != 1:
            return
        calculator = self.calculator(self.market_data)
        if not self.have_position() and not self.enough_amount():
            return
        ama = calculator.ama(self.window, fast_coefficient=5)
        self.__handle_long(ama)

    def __handle_long(self, ma):
        if ma is None or len(ma) < 5:
            return

        if self.have_position():
            if ma[-1] < ma[-2] < ma[-3]:
                self.close_position()
                return

            if self.market_data.close < ma[-1]:
                self.g.cross_ma += 1
            if self.market_data.close > ma[-1]:
                self.g.cross_ma = 0

            if self.g.cross_ma > 2:
                self.close_position()
                return
        else:  # 开仓判断
            if not ma[-1] > ma[-2] > ma[-3] > ma[-4]:
                return

            if ma[-1] - ma[-2] <= ma[-2] - ma[-3]:
                return
            if ma[-2] - ma[-3] <= ma[-3] - ma[-4]:
                return
            self.g.cross_ma = 0
            self.create_order(PositionSide.LONG, self.max_single_position)


class LLTStrategy(PositionDirectionManager, PositionRateManager, BaseStrategy):
    verbose_name = "均线(LLT)"
    """
    参考资料：
        https://bigquant.com/wiki/static/upload/5f/5fe20094-b60a-442f-a8e3-fda8a6175cbb.pdf
        https://www.joinquant.com/view/community/detail/bb6c3ae94085594c7c559d039a347409
        https://blog.csdn.net/weixin_42219751/article/details/123824815
        https://zhuanlan.zhihu.com/p/625553145
    """

    def __init__(self, ):
        self.d = 30
        self.d2 = 60
        self.k = Decimal("0.008")
        # self.window = 10

        # alpha = 2 / (d + 1)
        self.alpha1 = Decimal(2 / (self.d + 1))
        self.alpha2 = Decimal(2 / (self.d2 + 1))

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
    def _get_factor(self, alpha):
        a = alpha
        m1 = a - (a ** 2) / 4
        m2 = (a ** 2) / 2
        m3 = a - (a ** 2) * 3 / 4
        n1 = 2 * (1 - a)
        n2 = (1 - a) ** 2
        return m1, m2, m3, n1, n2

    def _calculate(self):
        """
        滤波器
        :return:
        """
        if self.g.pre_close is None:
            self.market_data.k = 0
            self.market_data.k2 = 0
            if self.market_data.finish != 1:
                return
            if self.g.pre_pre_close is None:
                self.g.pre_pre_close = self.market_data.close
                self.g.pre_pre_close2 = self.market_data.close
                self.g.pre_pre_llt = self.market_data.close
                self.g.pre_pre_llt2 = self.market_data.close
            else:
                self.g.pre_close = self.market_data.close
                self.g.pre_close2 = self.market_data.close
                self.g.pre_llt = self.alpha1 * self.market_data.close + self.g.pre_pre_llt * (1 - self.alpha1)
                self.g.pre_llt2 = self.alpha2 * self.market_data.close + self.g.pre_pre_llt2 * (1 - self.alpha2)
            return

        m1, m2, m3, n1, n2 = self._get_factor(self.alpha1)
        self.market_data.llt = m1 * self.market_data.close + m2 * self.g.pre_close - m3 * self.g.pre_pre_close + n1 * self.g.pre_llt - n2 * self.g.pre_pre_llt
        m1, m2, m3, n1, n2 = self._get_factor(self.alpha2)
        self.market_data.llt2 = m1 * self.market_data.close + m2 * self.g.pre_close2 - m3 * self.g.pre_pre_close2 + n1 * self.g.pre_llt2 - n2 * self.g.pre_pre_llt2
        self.market_data.k = self.market_data.llt / self.g.pre_llt - 1
        self.market_data.k2 = self.market_data.llt2 / self.g.pre_llt2 - 1
        if self.market_data.finish == 1:
            self.g.pre_pre_close = self.g.pre_close
            self.g.pre_pre_close2 = self.g.pre_close2
            self.g.pre_pre_llt = self.g.pre_llt
            self.g.pre_pre_llt2 = self.g.pre_llt2

            self.g.pre_close = self.market_data.close
            self.g.pre_close2 = self.market_data.close
            self.g.pre_llt = self.market_data.llt
            self.g.pre_llt2 = self.market_data.llt2

    def handle(self):
        """
        策略思路1：llt斜率大于阈值做多， 小于1平多；llt斜率小于阈值做空， 大于1平空；
        策略思路2：短均线向上穿过长均线，做多；短均线向下穿过长均线，平仓

        """
        self._calculate()
        # 策略思路1
        if self.have_position():
            if self.is_long_position() and self.market_data.k < 0:
                self.close_position("趋势结束(多头)")
            if self.is_short_position() and self.market_data.k > 0:
                self.close_position("趋势结束(空头)")
        else:
            if self.can_long() and self.market_data.k > self.k:
                self.create_order(PositionSide.LONG, self.max_single_position)

            if self.can_short() and self.market_data.k < -self.k:
                self.create_order(PositionSide.SHORT, self.max_single_position)

        # # 策略思路2
        # if self.have_position():
        #     if self.is_long_position() and self.market_data.llt2 > self.market_data.llt:
        #         self.close_position("趋势结束(多头)")
        #     if self.is_short_position() and self.market_data.llt2 < self.market_data.llt:
        #         self.close_position("趋势结束(空头)")
        # else:
        #     if self.can_long() and self.market_data.llt2 < self.market_data.llt and\
        #             self.market_data.llt > self.g.pre_pre_llt and self.market_data.llt2 > self.g.pre_pre_llt2\
        #             and self.market_data.close > self.market_data.llt:
        #         self.create_order(PositionSide.LONG, self.max_single_position)
        #     if self.can_short() and self.market_data.llt2 > self.market_data.llt and\
        #             self.market_data.llt < self.g.pre_pre_llt and self.market_data.llt2 < self.g.pre_pre_llt2\
        #             and self.market_data.close < self.market_data.llt:
        #         self.create_order(PositionSide.LONG, self.max_single_position)



if __name__ == '__main__':
    pass
