#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/04 20:36
# @Author  : shenglin.li
# @File    : strategy_area.py
# @Software: PyCharm
from decimal import Decimal

from leek.strategy import BaseStrategy
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.t import MA, KDJ, ATR
from leek.trade.trade import PositionSide


class AreaStrategy(DynamicRiskControl, PositionRateManager, PositionDirectionManager, BaseStrategy):
    """
    https://mp.weixin.qq.com/s?__biz=MzkyODI5ODcyMA==&mid=2247484161&idx=1&sn=85b980eb19f4d016b7f1a42ffa9bf7a5&scene=21

    """

    def __init__(self):
        self.threshold = Decimal("4")
        self.period = 60
        self.window = 9
        self.k_smoothing_factor = 3
        self.d_smoothing_factor = 3

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": max(self.window, self.period)
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.market_data = market_data
            self._calculate()

    def _calculate(self):
        if self.g.trend is None:
            self.g.ma = MA(self.period)
            self.g.kdj = KDJ(self.window, self.k_smoothing_factor, self.d_smoothing_factor)
            self.g.atr = ATR(self.window)

            self.g.area = 0
            self.g.trend = 1  # 1: 上涨趋势，-1: 下降趋势
            self.g.pre = None

        g = self.g
        kdj = g.kdj.update(self.market_data)
        atr = g.atr.update(self.market_data)
        if kdj:
            self.market_data.k = kdj[0]
            self.market_data.d = kdj[1]
            self.market_data.j = kdj[2]
        ma = g.ma.update(self.market_data)
        if ma is None:
            return False, None, None, None, None, g.pre

        price = self.market_data.close
        area = g.area
        reverse = False
        try:
            single_area = (price - ma) / ma
            if (g.trend == 1 and price > ma) or (g.trend == -1 and price < ma):
                area += single_area
            else:
                reverse = True
            self.market_data.area = area
            return reverse, area, kdj, ma, atr, g.pre
        finally:
            if self.market_data.finish == 1:
                g.pre = self.market_data
                g.area = area
                if reverse:
                    g.trend *= -1
                    g.area = 0

    def handle(self):
        """
        多头开仓信号：
        （1）下降趋势的“K线面积”达到阈值，之前成立即可；
        （2）KDJ指标值大于80；
        （3）价格涨超前一根K线最高价加一倍ATR。
        空头开仓信号：
        （1）上涨趋势的“K线面积”达到阈值，之前成立即可；
        （2）KDJ指标值小于20；
        （3）价格跌破前一根K线最低价减一倍ATR。
        多头/空头出场：ATR跟踪止损止盈。
        :return:
        """
        reverse, area, kdj, self.market_data.ma, atr, pre = self._calculate()
        if not self.have_position():
            if reverse and abs(area) > self.threshold:  # 发生反转阈值达标
                if area > 0 and self.can_short() and kdj[2] < 20 and self.market_data.close < pre.low - atr:
                    self.create_order(PositionSide.SHORT, self.max_single_position)
                if area < 0 and self.can_long() and kdj[2] > 80 and self.market_data.close > pre.high + atr:
                    self.create_order(PositionSide.LONG, self.max_single_position)
        else:
            pass




if __name__ == '__main__':
    pass
