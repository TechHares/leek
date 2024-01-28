#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:02
# @Author  : shenglin.li
# @File    : strategy_mean_reverting.py
# @Software: PyCharm
import decimal
import logging
from collections import deque
from decimal import Decimal

import numpy as np

from leek.common import G, logger
from leek.strategy.strategy import BaseStrategy
from leek.trade.trade import Order, PositionSide, OrderType


class MeanRevertingStrategy(BaseStrategy):
    """
    均线回归策略
    核心思想：没有只跌(涨)不涨(跌)的标的； 标的均值过大，做反向
    风险: 单边行情
    """

    def __init__(self, symbols=None, direction=PositionSide.FLAT, mean_type: str = "EMA", lookback_intervals=20,
                 threshold="0.1", take_profit_rate="0.3", stop_loss_rate="0.1", max_single_position="0.5",
                 fallback_percentage="0.05"):
        """
        :param symbols: 标的，多个标的「,」分割， 不填则不限标的
        :param mean_type: 均值计算方式 EMA 简单移动平均 EMA 指数移动平均
        :param direction: 方向
        :param lookback_intervals: 计算指标的过去时间段的长度
        :param threshold: 偏离阈值
        :param take_profit_rate: 质押比例
        :param stop_loss_rate: 止损比例
        :param max_single_position: 单个标的最大持仓比例
        :param fallback_percentage: 回撤止盈比例(未达到止盈比例时，发生回撤的止盈比例)
        """
        self.symbols = symbols.split(",") if symbols is not None and symbols.strip() != "" else None
        self.mean_type = mean_type.upper()
        self.lookback_intervals = int(lookback_intervals)
        self.threshold = Decimal(threshold)
        self.indicators = MACalculator(self.lookback_intervals, self.threshold, self.mean_type)
        self.take_profit_rate = Decimal(take_profit_rate)
        self.fallback_percentage = Decimal(fallback_percentage)
        self.stop_loss_rate = Decimal(stop_loss_rate)
        self.max_single_position = Decimal(max_single_position)
        if not isinstance(direction, PositionSide):
            direction = PositionSide(int(direction))
        self.direction = direction

        self.short_count = 0
        self.long_count = 0
        self.count = 0
        self.sell_count = 0

    def __calculate_z_score(self, market_data):
        """
        计算偏移值
        :return:
        """
        if market_data.finish == 1:
            self.indicators.add_element(market_data)

        els = self.indicators.get_elements()
        if els is None:
            return 0

        score1 = (market_data.close - els[-1].ma) / els[-1].ma
        score2 = (els[-1].close - els[-2].ma) / els[-2].ma
        score3 = (els[-2].close - els[-3].ma) / els[-3].ma

        score = (market_data.close - els[-1].ma) / els[-1].ma
        if abs(score) > self.threshold:
            if abs(score1) < self.threshold or abs(score2) < self.threshold or abs(score3) < self.threshold:
                return 0
            if score1 > score2 > score3 or score1 < score2 < score3:
                return score
        # if abs(score1) > self.threshold and abs(score2) > self.threshold and abs(score3) > self.threshold \
        #         and abs(score1) > np.mean([abs(score2), abs(score3)]):
        #     return score1

        return 0

    def is_long(self):
        return self.direction == PositionSide.LONG or self.direction == PositionSide.FLAT

    def is_short(self):
        return self.direction == PositionSide.SHORT or self.direction == PositionSide.FLAT

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
            # amount = min(self.max_single_position * max(self.total_amount, self.available_amount),
            amount = min(self.max_single_position * self.total_amount,
                         self.available_amount)
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

        #  有持仓
        position = self.position_map[market_data.symbol]
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1
        if rate > self.take_profit_rate or rate < -self.stop_loss_rate:  # 止盈止损
            self.sell_count += 1
            logger.info(f"止盈止损平仓：{position}")
            return position.get_close_order(self.job_id, f"MR{self.job_id}{self._get_seq_id()}",
                                            price=market_data.close)

        position.high_price = max(position.high_price, market_data.high) if hasattr(position, "high_price")\
            else market_data.high

        position.low_price = min(position.low_price, market_data.low) if hasattr(position, "low_price") else market_data.low

        if (position.high_price - market_data.close) / position.avg_price > self.fallback_percentage or \
                (market_data.close - position.low_price) / position.avg_price > self.fallback_percentage:
            self.sell_count += 1
            logger.info(f"回撤平仓：{position}")
            return position.get_close_order(self.job_id, f"MR{self.job_id}{self._get_seq_id()}",
                                            price=market_data.close)

    def shutdown(self):
        super(MeanRevertingStrategy, self).shutdown()
        print(f"开单：多单数{self.long_count} 空单数{self.short_count} 平仓数{self.sell_count}")


class MACalculator:
    def __init__(self, size, threshold, mean_type):
        self.threshold = threshold
        self.mean_type = mean_type
        self.size = size
        self.alpha = decimal.Decimal(0.2 / (size + 1))
        self.window = deque(maxlen=size)

    def add_element(self, element):
        if element.amount == 0 or element.volume == 0:
            return
        g = G(avg_price=element.amount / element.volume, close=element.close)
        g.ma = g.avg_price
        self.window.append(g)
        if self.mean_type == "SMA":
            g.ma = np.mean([e.avg_price for e in self.get_elements()])
            return
        ma = self.window[0].ma
        for i in range(1, len(self.window)):
            ma = self.alpha * self.window[i].ma + (1 - self.alpha) * ma
        g.ma = ma

    def get_elements(self):
        if self.size != len(self.window):
            return None
        return list(self.window)


if __name__ == '__main__':
    g = G()
    g.finish = 1

    print(g)
    print(g.finish)
