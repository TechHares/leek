#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:02
# @Author  : shenglin.li
# @File    : strategy_mean_reverting.py
# @Software: PyCharm
import decimal
from collections import deque
from decimal import Decimal

import numpy as np

from leek.common import G, logger
from leek.strategy import *
from leek.strategy.strategy import BaseStrategy
from leek.strategy.strategy_common import StopLoss
from leek.trade.trade import Order, PositionSide, OrderType


class MeanRevertingStrategy(SymbolsFilter, PositionDirectionManager, TakeProfit, StopLoss, CalculatorContainer,
                            FallbackTakeProfit, PositionRollingCalculator, BaseStrategy):
    verbose_name = "均值回归"
    """
    均值回归策略
    核心思想：没有只跌(涨)不涨(跌)的标的； 标的均值过大，做反向
    风险: 单边行情
    """

    def __init__(self, mean_type: str = "EMA", threshold="0.1", max_single_position="0.5"):
        """
        :param mean_type: 均值计算方式 EMA 简单移动平均 EMA 指数移动平均
        :param threshold: 偏离阈值
        :param max_single_position: 单个标的最大持仓比例
        """
        self.mean_type = mean_type.upper()
        self.threshold = Decimal(threshold)
        self.max_single_position = Decimal(max_single_position)

        self.short_count = 0
        self.long_count = 0
        self.count = 0
        self.sell_count = 0

    def __calculate_z_score(self, market_data):
        """
        计算偏移值
        :return:
        """
        calculator = self.calculator(market_data)

        if self.mean_type == "EMA":
            ma = calculator.ema(market_data.close)
        else:
            ma = calculator.sma(market_data.close)
        return (market_data.close - ma) / ma if ma > 0 else 0
        # if abs(score1) > self.threshold and abs(score2) > self.threshold and abs(score3) > self.threshold \
        #         and abs(score1) > np.mean([abs(score2), abs(score3)]):
        #     return score1

    def handle(self, market_data: G) -> Order:
        """
        均线回归策略
        1. 标的无持仓时，
            a. 计算偏移值: (price - MA) / MA, 大于0往上偏移, 小于0往下偏移
            b. 方向可操作 且 偏移值绝对值大于阈值， 买入(多/空)
        2. 标的有持仓时:
            a. 触发止盈止损 平仓
            b. 计算购买之后最高(低)点回撤， 止盈止损
        :param market_data: 市场数据
        :return: 交易指令
        """
        if self.symbols is not None and market_data.symbol not in self.symbols:  # 该标的不做
            return None

        if market_data.symbol not in self.position_map:  # 没有持仓
            z_score = self.__calculate_z_score(market_data)
            if z_score > self.threshold and self.is_short():  # 做空
                side = PositionSide.SHORT
            elif z_score < -self.threshold and self.is_long():  # 做多
                side = PositionSide.LONG
            else:
                return None
            amount = self.calculate_buy_amount(self.max_single_position, symbol=market_data.symbol)
            if amount < (self.max_single_position * self.total_amount / 2):  # 可用资金不足
                return None

            order = Order(self.job_id, f"MR{self.job_id}{self._get_seq_id()}", OrderType.MarketOrder,
                          market_data.symbol)
            if side == PositionSide.LONG:
                self.long_count += 1
            else:
                self.short_count += 1
            order.amount = amount
            order.side = side
            order.price = market_data.close
            order.order_time = market_data.timestamp
            logger.info(f"开仓：{order}")
            return order

        #  有持仓 使用公用策略止盈止损

    def shutdown(self):
        super(MeanRevertingStrategy, self).shutdown()
        print(f"开单：多单数{self.long_count} 空单数{self.short_count} 平仓数{self.sell_count}")


if __name__ == '__main__':
    g = G()
    g.finish = 1

    print(g)
    print(g.finish)
