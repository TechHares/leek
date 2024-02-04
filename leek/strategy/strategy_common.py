#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/31 17:13
# @Author  : shenglin.li
# @File    : strategy_common.py
# @Software: PyCharm
from abc import ABC
from decimal import Decimal

from leek.common import G, Calculator, logger
from leek.common.utils import get_defined_classes, get_constructor_args, decimal_quantize
from leek.strategy import BaseStrategy
from leek.trade import Order
from leek.trade.trade import PositionSide

"""
公用工具方法
"""


class SymbolFilter(object):
    """
    单标的过滤
    """

    def __init__(self, symbol=""):
        """
        :param symbol: 操作标的标识
        """
        self.symbol = symbol

    def pre(self, market_data: G) -> bool:
        return market_data.symbol == self.symbol


class SymbolsFilter(object):
    """
    多标的过滤
    """

    def __init__(self, symbols=""):
        """
        :param symbols: 标的，多个标的「,」分割， 不填则不限标的
        """
        self.symbols = symbols.split(",") if symbols is not None and symbols.strip() != "" else None

    def pre(self, market_data: G) -> bool:
        return self.symbols is None or market_data.symbol in self.symbols


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


class PositionRollingCalculator(BaseStrategy, ABC):
    """
    仓位计算（滚仓、定额）
    """

    def __init__(self, rolling_over=0):
        """
        :param rolling_over: 滚仓 默认 False
        """
        self.rolling_over = bool(int(rolling_over))
        self.window_container = {}

    def calculate_buy_amount(self, position_rate, symbol=None, max_single_position=1) -> Decimal:
        position_rate = Decimal(position_rate)
        max_single_position = Decimal(max_single_position)
        amount = decimal_quantize((self.available_amount + self.position_value) * position_rate, 2) if self.rolling_over \
            else decimal_quantize(self.total_amount * position_rate, 2)

        max_position = max_single_position * self.total_amount
        value = None
        if symbol is not None and symbol in self.position_map:
            value = self.position_map[symbol].value
            max_position -= value
        d = max(min(self.available_amount, amount, max_position), Decimal("0"))
        logger.info(f"计算开仓金额: 滚仓: {self.rolling_over} 初始金额: {self.total_amount} 剩余可用: {self.available_amount}"
                    f"持仓价值: {self.position_value if value is None else value}, 仓位: {position_rate}, 标的：{symbol}, 仓位限制：{max_single_position}"
                    f"金额：{d}")
        return d if d > Decimal("0") else 0


class PositionDirectionManager:
    """
    头寸方向(多/空/多和空)
    """

    def __init__(self, direction: PositionSide = PositionSide.FLAT):
        """
        :param direction: 头寸方向
        """
        if not isinstance(direction, PositionSide):
            direction = PositionSide(int(direction))
        self.direction = direction

    def is_long(self):
        return self.direction == PositionSide.LONG or self.direction == PositionSide.FLAT

    def is_short(self):
        return self.direction == PositionSide.SHORT or self.direction == PositionSide.FLAT


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


class StopLoss(BaseStrategy):
    """
    比例止损
    """

    def __init__(self, stop_loss_rate="0.1"):
        """
        :param stop_loss_rate: 止损比例
        """
        self.stop_loss_rate = Decimal(stop_loss_rate)

    def handle(self, market_data: G) -> Order:
        if market_data.symbol not in self.position_map:
            return None
        position = self.position_map[market_data.symbol]
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate < -self.stop_loss_rate:  # 止盈止损
            logger.info(
                f"止盈平仓：阈值={self.stop_loss_rate} 触发价格={market_data.close} 平均持仓价={position.avg_price} 触发比例={rate}")
            return self._close_position(market_data)


class TakeProfit(BaseStrategy):
    """
    比例止盈
    """

    def __init__(self, take_profit_rate="0.1"):
        """
        :param take_profit_rate: 止盈比例
        """
        self.take_profit_rate = Decimal(take_profit_rate)

    def handle(self, market_data: G) -> Order:
        if market_data.symbol not in self.position_map:
            return None
        position = self.position_map[market_data.symbol]
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate > self.take_profit_rate:  # 止盈
            logger.info(
                f"止盈平仓：阈值={self.take_profit_rate} 触发价格={market_data.close} 平均持仓价={position.avg_price} 触发比例={rate}")
            return self._close_position(market_data)


class FallbackTakeProfit(BaseStrategy):
    """
    回撤止盈
    """

    def __init__(self, fallback_percentage="0.05"):
        """

        :param fallback_percentage: 回撤止盈的比例
        """
        self.fallback_percentage = Decimal(fallback_percentage)
        self.fallback_container = {}

    def handle(self, market_data: G) -> Order:
        if market_data.symbol not in self.position_map:
            return None

        if market_data.symbol not in self.fallback_container:
            self.fallback_container[market_data.symbol] = G(high=market_data.high, low=market_data.low)

        g = self.fallback_container[market_data.symbol]
        g.high = max(g.high, market_data.high)
        g.low = min(g.low, market_data.low)

        position = self.position_map[market_data.symbol]
        rate = (g.high - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate = (market_data.close - g.low) / position.avg_price

        if rate > self.fallback_percentage:  # 回撤止盈
            logger.info(
                f"回撤止盈平仓：阈值={self.fallback_percentage} 触发价格={market_data.close} 平均持仓价={position.avg_price} 触发比例={rate}")
            return self._close_position(market_data)


PRE_STRATEGY_LIST = [SymbolsFilter, SymbolFilter]
RISK_STRATEGY_LIST = [StopLoss, TakeProfit, FallbackTakeProfit]
if __name__ == '__main__':
    classes = get_defined_classes("leek.strategy.strategy_common")
    __package__ = "leek.strategy.strategy_common"
    for cls in classes:
        print(get_constructor_args(cls))
    print(classes)
