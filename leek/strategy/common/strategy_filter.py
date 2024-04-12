#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/31 17:13
# @Author  : shenglin.li
# @File    : strategy_common.py
# @Software: PyCharm
from abc import abstractmethod
from decimal import Decimal

from leek.common import G
from leek.strategy.common.strategy_common import CalculatorContainer
from leek.trade.trade import PositionSide

"""
前置过滤策略
"""


class Filter:

    @abstractmethod
    def pre(self, market_data: G, position):
        """
        是否需要执行策略
        :param market_data: 市场数据
        :param position: 持仓数据
        :param strategy: 策略
        :return: True 可以执行 False 阻断执行
        """
        return True


class SymbolFilter(Filter):
    """
    单标的过滤
    """

    def __init__(self, symbol=""):
        """
        :param symbol: 操作标的标识
        """
        self.symbol = symbol

    def pre(self, market_data: G, position) -> bool:
        return market_data.symbol == self.symbol


class SymbolsFilter(Filter):
    """
    多标的过滤
    """

    def __init__(self, symbols=""):
        """
        :param symbols: 标的，多个标的「,」分割， 不填则不限标的
        """
        self.symbols = symbols.split(",") if symbols is not None and symbols.strip() != "" else None

    def pre(self, market_data: G, position) -> bool:
        return self.symbols is None or market_data.symbol in self.symbols


class StopLoss(Filter):
    """
    比例止损
    """

    def __init__(self, stop_loss_rate="0.1"):
        """
        :param stop_loss_rate: 止损比例
        """
        self.stop_loss_rate = Decimal(stop_loss_rate)

    def pre(self, market_data: G, position) -> bool:
        if position is None:
            return True
        rate = (position.quantity_amount - market_data.close * position.quantity) / position.quantity_amount
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate < -self.stop_loss_rate:  # 止盈止损
            self.close_position(memo=f"止盈平仓：阈值={self.stop_loss_rate} "
                                     f"触发价格={market_data.close}"
                                     f" 平均持仓价={position.quantity_amount / market_data.close} 触发比例={rate}")
            return False
        return True


class TakeProfit(Filter):
    """
    比例止盈
    """

    def __init__(self, take_profit_rate="0.1"):
        """
        :param take_profit_rate: 止盈比例
        """
        self.take_profit_rate = Decimal(take_profit_rate)

    def pre(self, market_data: G, position) -> bool:
        if position is None:
            return True
        rate = (position.quantity_amount - market_data.close * position.quantity) / position.quantity_amount
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate > self.take_profit_rate:  # 止盈
            self.close_position(memo=f"止盈平仓：阈值={self.take_profit_rate} "
                                     f"触发价格={market_data.close} 平均持仓价={position.quantity_amount / position.quantity}"
                                     f" 触发比例={rate}")
            return False
        return True


class FallbackTakeProfit(Filter):
    """
    回撤止盈
    """

    def __init__(self, fallback_percentage="0.05"):
        """

        :param fallback_percentage: 回撤止盈的比例
        """
        self.fallback_percentage = Decimal(fallback_percentage)
        self.fallback_container = {}

    def pre(self, market_data: G, position) -> bool:
        if position is None:
            return True

        if market_data.symbol not in self.fallback_container:
            self.fallback_container[market_data.symbol] = G(high=market_data.high, low=market_data.low)

        g = self.fallback_container[market_data.symbol]
        g.high = max(g.high, market_data.high)
        g.low = min(g.low, market_data.low)

        if position.direction == PositionSide.SHORT:
            rate = (market_data.close - g.low) * position.quantity / position.quantity_amount
        else:
            rate = (g.high - market_data.close) * position.quantity / position.quantity_amount

        if rate > self.fallback_percentage:  # 回撤止盈
            self.close_position(memo=f"回撤止盈平仓：阈值={self.fallback_percentage}"
                                     f" 触发价格={market_data.close} "
                                     f"最高价={g.high} 触发比例={rate}")
            return False
        return True


class AtrStopLoss(CalculatorContainer, Filter):
    """
    ATR动态止损， 根据当前波动率动态调整止损
    """

    def __init__(self, atr_coefficient="1"):
        """
        :param atr_coefficient: atr系数， 根据风险偏好，越大止损范围越大
        """
        self.atr_stop_loss_coefficient = float(atr_coefficient)  # 动态止损系数

    def pre(self, market_data: G, position):
        if position is None:
            return True
        dt_price = market_data.close - position.avg_price
        if position.direction == PositionSide.SHORT:
            dt_price *= -1

        calculator = self.calculator(market_data)
        atr = calculator.atr(1)
        if atr is None:
            return True
        if dt_price < -self.atr_stop_loss_coefficient * atr[0]:  # 止损
            self.close_position(memo=f"ATR动态止损：比例={self.atr_stop_loss_coefficient} * {atr[0]} "
                                     f"触发价格={market_data.close} 平均持仓价={position.avg_price} 触发差价={dt_price}")
            return False
        return True


PRE_STRATEGY_LIST = [SymbolsFilter, SymbolFilter, StopLoss, TakeProfit, FallbackTakeProfit]
if __name__ == '__main__':
    pass
