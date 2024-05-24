#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/17 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
from leek.common import G
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.trade.trade import PositionSide


class TDStrategy(PositionDirectionManager, DynamicRiskControl, PositionRateManager, BaseStrategy):
    verbose_name = "TD组合"

    """
    GFTDV2模型
    docs/indicator/td.md
    """

    def __init__(self, window=4, fast_period=4, slow_period=4):
        """
        :param window: 前馈间隔
        :param fast_period: 启动计数
        :param slow_period: 买入/卖出计数
        """
        self.n1 = int(window)
        self.n2 = int(fast_period)
        self.n3 = int(slow_period)

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": self.n2
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.market_data = market_data
            self._calculate(self.g)

    def _calculate(self, ctx):
        if ctx.data is None:
            ctx.data = []
        self.market_data.ud = 0
        self.market_data.count = 0

        if len(ctx.data) < self.n1 - 1:
            return
        price = self.market_data.close
        # 1. 计算ud
        if price > ctx.data[-self.n1+1].close:
            self.market_data.ud = 1
        if price < ctx.data[-self.n1+1].close:
            self.market_data.ud = -1

        # 2. count
        self.market_data.count = self.market_data.ud
        idx = 0
        for i in range(1, len(ctx.data)):
            idx = i
            if ctx.data[-i].ud == self.market_data.ud:
                self.market_data.count += ctx.data[-i].ud
            else:
                break
        ctx.data = ctx.data[-max(idx, self.n1 - 1):]

        # 3. 启动
        if self.market_data.count >= self.n2:
            ctx.sell_start = True
            ctx.sell_count = 0
            ctx.sell_count_price = price
            ctx.high_in_count = self.market_data.high
        if self.market_data.count <= -self.n2:
            ctx.buy_start = True
            ctx.buy_count = 0
            ctx.buy_count_price = price
            ctx.low_in_count = self.market_data.low

        # 4. 买入计数
        if ctx.buy_start and price >= ctx.data[-2].high and self.market_data.high > ctx.data[-1].high and \
                price > ctx.buy_count_price:
            ctx.buy_count_price = price
            ctx.low_in_count = min(self.market_data.low, ctx.low_in_count)
            ctx.buy_count += 1
        # 5. 卖出计数
        if ctx.sell_start and price <= ctx.data[-2].high and self.market_data.low < ctx.data[-1].low and \
                price < ctx.sell_count_price:
            ctx.sell_count += 1
            ctx.sell_count_price = price
            ctx.high_in_count = max(self.market_data.high, ctx.high_in_count)
        ctx.data.append(self.market_data)

    def handle(self):
        # ctx = G(**self.g.__json__())
        if self.market_data.finish != 1:
            return
        ctx = self.g
        self._calculate(ctx)
        ctx.data.append(self.market_data)

        if self.have_position():
            if self.is_long_position():
                if self.market_data.close < ctx.loss_price:
                    self.close_position("止损(多)")
                    return
                if ctx.sell_count == self.n3:
                    self.close_position("出局(多)")
                    return
            if self.is_short_position():
                if self.market_data.close > ctx.loss_price:
                    self.close_position("止损(空)")
                    return
                if ctx.buy_count == self.n3:
                    self.close_position("出局(空)")
                    return
        else:
            if self.can_short() and ctx.sell_count == self.n3:
                ctx.sell_start = False
                ctx.sell_count = 0
                ctx.loss_price = ctx.high_in_count
                self.create_order(PositionSide.SHORT, self.max_single_position)

            if self.can_long() and ctx.buy_count == self.n3:
                ctx.buy_start = False
                ctx.buy_count = 0
                ctx.loss_price = ctx.low_in_count
                self.create_order(PositionSide.LONG, self.max_single_position)


if __name__ == '__main__':
    pass
