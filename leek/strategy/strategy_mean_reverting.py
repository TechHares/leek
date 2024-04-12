#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:02
# @Author  : shenglin.li
# @File    : strategy_mean_reverting.py
# @Software: PyCharm
from decimal import Decimal

from leek.common import G
from leek.strategy import *
from leek.strategy.common import *
from leek.strategy.common.strategy_common import PositionRateManager
from leek.trade.trade import PositionSide


class MeanRevertingStrategy(PositionRateManager, SymbolsFilter, PositionDirectionManager, TakeProfit, StopLoss, CalculatorContainer,
                            FallbackTakeProfit, BaseStrategy):
    verbose_name = "均值回归"
    """
    均值回归策略
    核心思想：没有只跌(涨)不涨(跌)的标的； 标的均值过大，做反向
    风险: 单边行情
    """

    def __init__(self, mean_type: str = "EMA", threshold="0.1"):
        """
        :param mean_type: 均值计算方式 EMA 简单移动平均 EMA 指数移动平均
        :param threshold: 偏离阈值
        """
        self.mean_type = mean_type.upper()
        self.threshold = Decimal(threshold)

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

    def handle(self):
        """
        均线回归策略
        1. 标的无持仓时，
            a. 计算偏移值: (price - MA) / MA, 大于0往上偏移, 小于0往下偏移
            b. 方向可操作 且 偏移值绝对值大于阈值， 买入(多/空)
        2. 标的有持仓时:
            a. 触发止盈止损 平仓
            b. 计算购买之后最高(低)点回撤， 止盈止损
        """
        if not self.have_position():  # 没有持仓
            if not self.enough_amount():
                return
            z_score = self.__calculate_z_score(self.market_data)
            if z_score > self.threshold and self.can_short():  # 做空
                side = PositionSide.SHORT
            elif z_score < -self.threshold and self.can_long():  # 做多
                side = PositionSide.LONG
            else:
                return

            self.create_order(side, position_rate=self.max_single_position)
        #  有持仓 使用公用策略止盈止损

    def shutdown(self):
        super(MeanRevertingStrategy, self).shutdown()


if __name__ == '__main__':
    g = G()
    g.finish = 1

    print(g)
    print(g.finish)
