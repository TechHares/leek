#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/19 15:48
# @Author  : shenglin.li
# @File    : evaluation.py
# @Software: PyCharm
from decimal import Decimal

import numpy as np

from leek.runner.runner import BaseWorkflow
from leek.trade.trade import PositionSide


class RoamingLoongEvaluationWorkflow(BaseWorkflow):
    """
    策略快速评估
    """

    def __init__(self, loss_rate=0):
        self.loss_rate = loss_rate

        self.trade_count = 0
        self.abs_profit = Decimal("1")
        self.rolling_profit = Decimal("1")

        self.rolling_profit_list = []
        self.abs_profit_list = []
        self.position_price = None
        self.position_direction = None

    def handle_data(self, price):
        if self.position_price is None:
            self.rolling_profit_list.append(self.rolling_profit)
            self.abs_profit_list.append(self.abs_profit)
        else:
            abs_profit, rolling_profit = self.__compute_profit(price)
            self.rolling_profit_list.append(rolling_profit)
            self.abs_profit_list.append(abs_profit)

    def close_trade(self, price):
        self.trade(PositionSide.switch_side(self.position_direction), price)

    def trade(self, direction, price):
        if self.position_price is None:
            self.position_price = price
            self.position_direction = direction
        else:
            self.trade_count += 1
            abs_profit, rolling_profit = self.__compute_profit(price, self.loss_rate)
            self.abs_profit = abs_profit
            self.rolling_profit = rolling_profit
            self.position_price = None
            self.position_direction = None

    def __compute_profit(self, price, loss_rate=0):
        rate = price / self.position_price
        if PositionSide.LONG == self.position_direction:
            return self.abs_profit + (rate - 1) - 2 * loss_rate, self.rolling_profit * rate * (1 - 2 * loss_rate)
        else:
            return self.abs_profit + (1 - rate) - 2 * loss_rate, self.rolling_profit / rate * (1 - 2 * loss_rate)

    def get_eval_data(self, t="roll"):
        """
        :param t: abs/roll 绝对收益/滚动收益
        :return:
        """

        if t == "abs":
            arr = np.array(self.abs_profit_list)
        else:
            arr = np.array(self.rolling_profit_list)

        # 计算累积最大值
        max_so_far = np.maximum.accumulate(arr)
        # 计算当前值与累积最大值之间的差值
        draw_downs = (max_so_far - arr) / max_so_far
        return self.trade_count, arr[-1], np.max(draw_downs)

    def have_position(self):
        return self.position_price is not None


if __name__ == '__main__':
    pass
