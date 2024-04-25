#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:47
# @Author  : shenglin.li
# @File    : strategy_grid.py
# @Software: PyCharm

from leek.common import EventBus
from leek.common.utils import *
from leek.strategy.common import *
from leek.strategy import BaseStrategy
from leek.trade.trade import Order, PositionSide as PS, OrderType as OT


class SingleGridStrategy(SymbolFilter, PositionSideManager, BaseStrategy):
    verbose_name = "单标的单方向网格策略"
    """
    单标的单方向网格策略
    """

    def __init__(self, min_price: Decimal = 1, max_price: Decimal = 0, risk_rate=0.1, grid: int = 10):
        """
        策略初始化
        :param min_price: 网格最小价格
        :param max_price: 网格最大价格
        :param risk_rate: 风控比例， 默认0.1，超出最小最大值系数之后直接平仓
        :param grid: 网格数量， 默认10
        """
        self.min_price = Decimal(min_price)
        self.max_price = Decimal(max_price)
        if self.min_price < 0 or self.max_price < 0 or self.min_price > self.max_price:
            raise RuntimeError(f"网格价格区间「{min_price}」-「{max_price}」设置不正确")
        self.risk_rate = Decimal(risk_rate)
        self.grid = int(grid)
        if self.grid < 0:
            raise RuntimeError(f"网格个数「{self.grid}」设置不正确")

        # 单个网格价格
        self.grid_price = decimal_quantize(((self.max_price - self.min_price) / self.grid), 8)

        # 运行数据
        self.current_grid = Decimal("0")
        self.last_price = Decimal("0")
        self.risk = False  # 是否已经风控

    def post_constructor(self):
        super().post_constructor()
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.handle_position)

    def handle(self):
        """
        网格策略:
            1. 网格区间 min_price ~ max_price, 价格 在 min_price(1 - risk_rate) ~ max_price(1 + risk_rate) 之外清仓
            2. 应持仓层数
                多: 应持仓层数 = (max_price - current_price) / grid_price
                空: 应持仓层数 = (current_price - min_price) / grid_price
            3. 操作
                多: 应持仓层数 > current_grid 买入，应持仓层数 < current_grid 卖出
                空: 应持仓层数 > current_grid 卖出，应持仓层数 < current_grid 买入
        :param market_data: 市场数据
        :return: 交易指令
        """
        market_data = self.market_data
        price = market_data.close
        if price > self.max_price * (1 + self.risk_rate) or price < self.min_price * (1 - self.risk_rate):
            if self.current_grid > 0:  # 有持仓
                self.notify(f"SingleGridStrategy 价格{price}超出风控范围{self.min_price * (1 - self.risk_rate)}"
                            f"-{self.max_price * (1 + self.risk_rate)} 平仓")
                self.g.gird = 0
                self.close_position("网格风控")
                self.risk = True
                return

        if price > self.max_price or price < self.min_price:  # 网格之外
            return
        if self.is_long():
            dt_price = self.max_price - price
        else:
            dt_price = price - self.min_price

        dt_gird = decimal_quantize(dt_price / self.grid_price, 0, 1)
        if dt_gird == self.current_grid:
            return
        if abs(self.last_price - price) < self.grid_price / 2:
            return
        if self.risk:  # 已经风控
            if dt_gird < 3 or dt_gird > 8:
                return
            dt_gird = 1
            self.risk = False

        self.last_price = price

        side = PS.LONG
        if dt_gird > self.current_grid:
            if self.is_short():  # 空
                side = PS.switch_side(side)
        else:
            side = PS.SHORT
            if self.is_short():  # 空
                side = PS.switch_side(side)

        self.notify(
            f"方向{self.side} 操作方向{side}"
            f" 网格数{self.current_grid}/{self.grid} 开仓：{abs(self.current_grid - dt_gird) / self.grid}\n"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{dt_gird}\n"
        )
        # si = "卖" if self.direction != order.side else "买"
        # print(f"网格数{self.current_grid} -> {dt_gird}, 资金: {self.available_amount} + {self.position_value} ="
        #       f" {self.available_amount + self.position_value} , {si} {order.amount}")
        self.g.gird = dt_gird
        self.create_order(side, abs(self.current_grid - dt_gird) / self.grid)

    def handle_position(self, order):
        self.current_grid = self.g.gird
        si = "卖" if self.side != order.side else "买"
        print(
            f"网格购买成功 -> {self.g.gird}, 资金: {self.position_manager.available_amount} + {self.position_manager.position_value} ="
            f" {self.position_manager.available_amount + self.position_manager.position_value} , {si} {order.amount}")

    def to_dict(self):
        d = super().to_dict()
        d["current_grid"] = self.current_grid.__str__()
        d["last_price"] = self.last_price.__str__()
        d["risk"] = self.risk
        return d

    def set_dict_data(self, data):
        super().set_dict_data(data)

        if "current_grid" in data:
            self.current_grid = Decimal(data["current_grid"])
        if "last_price" in data:
            self.last_price = Decimal(data["last_price"])
        if "risk" in data:
            self.risk = data["risk"]


if __name__ == '__main__':
    pass
