#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/31 17:13
# @Author  : shenglin.li
# @File    : strategy_common.py
# @Software: PyCharm
from abc import abstractmethod
from collections import deque
from decimal import Decimal

from leek.common import G, logger
from leek.common.utils import decimal_quantize
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
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate < -self.stop_loss_rate:  # 止盈止损
            self.close_position(memo=f"止损平仓：阈值={self.stop_loss_rate} "
                                     f"触发价格={market_data.close}"
                                     f" 平均持仓价={position.avg_price} 触发比例={rate}")
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
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1

        if rate > self.take_profit_rate:  # 止盈
            self.close_position(memo=f"止盈平仓：阈值={self.take_profit_rate} "
                                     f"触发价格={market_data.close} 平均持仓价={position.avg_price}"
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


class JustFinishKData(Filter):
    """
    仅使用已完成的K线数据
    """

    def __init__(self, just_finish_k=False):
        """

        :param just_finish_k: 仅使用完成的K线数据
        """
        x = str(just_finish_k).lower()
        self.all_k = x not in ["true", 'on', 'open', '1']

    def pre(self, market_data: G, position) -> bool:
        return self.all_k or market_data.finish == 1


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


class DynamicRiskControl(Filter):
    """
    无序的震荡可能会连续地止损，迅速移至成本非常地重要
    """

    def __init__(self, window=13, atr_coefficient="1", stop_loss_rate="0.1"):
        """
        :param atr_coefficient: atr系数， 根据风险偏好，越大止损范围越大
        :param stop_loss_rate: 止损比例
        """
        self.atr_stop_loss_coefficient = decimal_quantize(Decimal(atr_coefficient), 3)  # 动态
        self.stop_loss_rate = Decimal(stop_loss_rate)  # 动态

        self.tr_window = int(window)
        self.risk_container = {}

    def pre(self, market_data: G, position):
        if market_data.symbol not in self.risk_container:
            self.risk_container[market_data.symbol] = G(trs=deque(maxlen=self.tr_window),
                                                        high=market_data.high, low=market_data.low)

        ctx = self.risk_container[market_data.symbol]
        atr = (sum(list(ctx.trs)) + (market_data.high - market_data.low)) / (len(ctx.trs) + 1)
        if market_data.finish == 1:
            ctx.trs.append(market_data.high - market_data.low)

        if position is None:
            ctx.high = market_data.high
            ctx.low = market_data.low
            if market_data.finish == 0:
                if ctx.risk_control:
                    return False
            else:
                ctx.risk_control = False
            return True

        if ctx.stop_loss_price is None:
            if position.direction == PositionSide.SHORT:
                ctx.stop_loss_price = min(max(market_data.high, ctx.high, market_data.close + self.atr_stop_loss_coefficient * atr),
                                          market_data.close * (1 + self.stop_loss_rate))
            else:
                ctx.stop_loss_price = max(min(market_data.low, ctx.low, market_data.close - self.atr_stop_loss_coefficient * atr),
                                          market_data.close * (1 - self.stop_loss_rate))
            return True

        if position.direction == PositionSide.SHORT and self.short_risk(market_data, ctx, atr):
            ctx.risk_control = True
            self.close_position(memo=f"动态平仓：系数={self.atr_stop_loss_coefficient} 退出价={ctx.stop_loss_price}"
                                     f"触发价格={market_data.close} 平均持仓价={position.avg_price}"
                                     f" 差价={position.avg_price-market_data.close}")

            return True
        if position.direction == PositionSide.LONG and self.long_risk(market_data, ctx, atr):
            ctx.risk_control = True
            self.close_position(memo=f"动态平仓：系数={self.atr_stop_loss_coefficient} 退出价={ctx.stop_loss_price}"
                                     f"触发价格={market_data.close} 平均持仓价={position.avg_price}"
                                     f" 差价={ market_data.close - position.avg_price}")
            return True

        if position.direction == PositionSide.SHORT and (market_data.close < position.avg_price - atr or market_data.close < position.avg_price * (1 - self.stop_loss_rate)):
            if ctx.stop_loss_price > position.avg_price:
                stop_loss_price = (position.avg_price + market_data.close) / 2
            else:
                stop_loss_price = min(position.avg_price, market_data.close + self.atr_stop_loss_coefficient * atr)
            if stop_loss_price < ctx.stop_loss_price:
                logger.info(f"止损价下移: 系数={self.atr_stop_loss_coefficient} atr={atr} 当前价格={market_data.close} ||"
                            f" {ctx.stop_loss_price} -> {stop_loss_price}")
                ctx.stop_loss_price = stop_loss_price
        if position.direction == PositionSide.LONG and (market_data.close > position.avg_price + atr or market_data.close > position.avg_price * (1 + self.stop_loss_rate)):
            if ctx.stop_loss_price < position.avg_price:
                stop_loss_price = (position.avg_price + market_data.close) / 2
            else:
                stop_loss_price = max(position.avg_price, market_data.close - self.atr_stop_loss_coefficient * atr)
            if stop_loss_price > ctx.stop_loss_price:
                logger.info(f"止损价上移: 持仓价={position.avg_price} atr={atr} 当前价格={market_data.close} ||"
                            f" {ctx.stop_loss_price} -> {stop_loss_price}")
                ctx.stop_loss_price = stop_loss_price

        return True

    @staticmethod
    def long_risk(market_data, ctx, atr):
        if market_data.close < ctx.stop_loss_price:
            return True

        if market_data.finish == 0:
            return False

        needle = market_data.high - market_data.close  # 阴线实体部分也计入
        if needle < atr:  # 短阴线不处理
            return False

        return needle > 3 * abs(market_data.open - market_data.close)

    @staticmethod
    def short_risk(market_data, ctx, atr):
        if market_data.close > ctx.stop_loss_price:
            return True

        if market_data.finish == 0:
            return False

        needle = market_data.close - market_data.low  # 阴线实体部分也计入
        if needle < atr:  # 短阴线不处理
            return False

        return needle > 3 * abs(market_data.open - market_data.close)


PRE_STRATEGY_LIST = [SymbolsFilter, SymbolFilter, StopLoss, TakeProfit, FallbackTakeProfit]
if __name__ == '__main__':
    pass
