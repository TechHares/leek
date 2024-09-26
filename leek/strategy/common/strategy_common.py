#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/31 17:13
# @Author  : shenglin.li
# @File    : strategy_common.py
# @Software: PyCharm
from decimal import Decimal

from leek.common import G
from leek.strategy.common.calculator import Calculator
from leek.trade.trade import PositionSide

"""
公用工具方法
"""


class CalculatorContainer:
    """
    K线数据容器
    """

    def __init__(self, window=20):
        """
        :param window: 计算指标的过去时间段的窗口长度
        """
        self.window = int(window)
        self.window_container = {}

    def calculator(self, market_data: G) -> Calculator:
        if market_data.symbol not in self.window_container:
            self.window_container[market_data.symbol] = Calculator(self.window)
        if market_data.finish == 1:
            self.window_container[market_data.symbol].add_element(market_data)
        return self.window_container[market_data.symbol]


# class PositionRollingCalculator(BaseStrategy, ABC):
#     """
#     仓位计算（滚仓、定额）
#     """
#
#     def __init__(self, rolling_over=0):
#         """
#         :param rolling_over: 滚仓 默认 False
#         """
#         self.rolling_over = bool(int(rolling_over))
#         self.window_container = {}
#
#     def calculate_buy_amount(self, position_rate, symbol=None, max_single_position=1) -> Decimal:
#         position_rate = Decimal(position_rate)
#         max_single_position = Decimal(max_single_position)
#         amount = decimal_quantize((self.available_amount + self.position_value) * position_rate, 2) if self.rolling_over \
#             else decimal_quantize(self.total_amount * position_rate, 2)
#
#         max_position = max_single_position * self.total_amount
#         value = None
#         if symbol is not None and symbol in self.position_map:
#             value = self.position_map[symbol].value
#             max_position -= value
#         d = max(min(self.available_amount, amount, max_position), Decimal("0"))
#         logger.info(f"计算开仓金额: 滚仓: {self.rolling_over} 初始金额: {self.total_amount} 剩余可用: {self.available_amount}"
#                     f"持仓价值: {self.position_value if value is None else value}, 仓位: {position_rate}, 标的：{symbol}, 仓位限制：{max_single_position}"
#                     f"金额：{d}")
#         return d if d > Decimal("0") else 0


class PositionDirectionManager:
    """
    头寸方向(多/空/多和空)
    """

    def __init__(self, direction: PositionSide | int | str = PositionSide.FLAT):
        """
        :param direction: 头寸方向
        """
        if not isinstance(direction, PositionSide):
            direction = PositionSide(int(direction))
        self.direction = direction

    def can_long(self):
        return self.direction == PositionSide.LONG or self.direction == PositionSide.FLAT

    def can_short(self):
        return self.direction == PositionSide.SHORT or self.direction == PositionSide.FLAT

    def can_do(self, side: PositionSide):
        return (self.can_long() and side == PositionSide.LONG) or (self.can_short() and side == PositionSide.SHORT)


class PositionSideManager:
    """
    头寸方向(多/空)
    """

    def __init__(self, side: PositionSide = PositionSide.FLAT):
        """
        :param side: 头寸方向
        """
        if not isinstance(side, PositionSide):
            side = PositionSide(int(side))
        self.side = side

    def is_long(self):
        return self.side == PositionSide.LONG

    def is_short(self):
        return self.side == PositionSide.SHORT


class PositionRateManager:
    """
    最大仓位
    """

    def __init__(self, max_single_position):
        """
        :param max_single_position: 最大仓位
        """
        self.max_single_position = Decimal(max_single_position)


if __name__ == '__main__':
    pass
