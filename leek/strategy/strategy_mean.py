#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/3/18 15:19
# @Author  : shenglin.li
# @File    : strategy_macd.py
# @Software: PyCharm

from leek.common import G
from leek.strategy import *
from leek.strategy.common import Calculator
from leek.strategy.common.strategy_common import PositionRateManager, CalculatorContainer
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


if __name__ == '__main__':
    pass
