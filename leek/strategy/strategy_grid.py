#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:47
# @Author  : shenglin.li
# @File    : strategy_grid.py
# @Software: PyCharm

from leek.common import EventBus
from leek.common.utils import *
from leek.strategy.strategy import BaseStrategy
from leek.trade.trade import Order, PositionSide as PS, OrderType as OT


class SingleGridStrategy(BaseStrategy):
    """
    单目标单方向网格策略
    """

    def __init__(self, symbol=None, min_price: Decimal = 1, max_price: Decimal = 0,
                 risk_rate=0.1, grid: int = 10, direction: PS = PS.LONG, rolling_over: bool = False):
        """
        策略初始化
        :param symbol: 操作目标标识
        :param min_price: 网格最小价格
        :param max_price: 网格最大价格
        :param risk_rate: 风控比例， 默认0.1，超出最小最大值系数之后直接平仓
        :param grid: 网格数量， 默认10
        :param direction: 操作方向 默认 多
        :param rolling_over: 滚仓 默认 False
        """
        self.symbol = symbol
        self.min_price = Decimal(min_price)
        self.max_price = Decimal(max_price)
        if self.min_price < 0 or self.max_price < 0 or self.min_price > self.max_price:
            raise RuntimeError(f"网格价格区间「{min_price}」-「{max_price}」设置不正确")
        self.risk_rate = Decimal(risk_rate)
        self.grid = int(grid)
        if self.grid < 0:
            raise RuntimeError(f"网格个数「{self.grid}」设置不正确")
        if not isinstance(direction, PS):
            direction = PS(int(direction))
        self.direction = direction
        self.rolling_over = bool(int(rolling_over))
        # 单个网格价格
        self.grid_price = decimal_quantize(((self.max_price - self.min_price) / self.grid), 8)

        # 运行数据
        self.current_grid = Decimal("0")
        self.last_price = Decimal("0")
        self.risk = False  # 是否已经风控

    def handle(self, market_data) -> Order:
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
        if market_data.symbol != self.symbol:
            return

        price = market_data.close
        if price > self.max_price * (1 + self.risk_rate) or price < self.min_price * (1 - self.risk_rate):
            if self.current_grid > 0:  # 有持仓
                self.notify(f"SingleGridStrategy 价格{price}超出风控范围{self.min_price * (1 - self.risk_rate)}"
                            f"-{self.max_price * (1 + self.risk_rate)} 平仓")
                o = self.position_map[self.symbol].get_close_order(self.job_id,
                                                                   f"C{self.job_id}{self._get_seq_id()}", price)
                o.extend = 0
                o.order_time = market_data.timestamp
                self.risk = True
                return o

        if price > self.max_price or price < self.min_price:  # 网格之外
            return
        if self.direction == PS.LONG or self.direction == PS.LONG.value:
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
        order = Order(strategy_id=self.job_id,
                      order_id=f"SG{self.job_id}{self._get_seq_id()}",
                      price=price,
                      tp=OT.MarketOrder,
                      symbol=self.symbol)
        if dt_gird > self.current_grid:
            order.side = PS.LONG
            if self.direction == PS.SHORT:  # 空
                order.side = PS.switch_side(order.side)
        else:
            order.side = PS.SHORT
            if self.direction == PS.SHORT:  # 空
                order.side = PS.switch_side(order.side)

        if order.side == self.direction:  # 开仓
            if not self.rolling_over:
                order.amount = decimal_quantize(self.total_amount / self.grid * abs(self.current_grid - dt_gird), 2)
            else:  # 滚仓
                order.amount = decimal_quantize(self.available_amount / (self.grid - self.current_grid)
                                                * abs(self.current_grid - dt_gird), 2)
            order.amount = min(self.available_amount, order.amount)
        else:  # 平仓
            order.amount = decimal_quantize(self.position_value / self.current_grid
                                            * abs(self.current_grid - dt_gird), 2)
            order.amount = min(self.position_value, order.amount)
        order.extend = dt_gird
        self.notify(
            f"总投入{self.total_amount} 方向{self.direction} 已投入{self.total_amount}"
            f" 网格数{self.current_grid}/{self.grid} \n"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{dt_gird}\n"
            f"操作方向{order.side} 最大可投= {self.available_amount}\n"
            f"金额:{order.amount}=math.floor({self.total_amount}/{self.grid}*abs({self.current_grid}-{dt_gird}))"
        )
        # si = "卖" if self.direction != order.side else "买"
        # print(f"网格数{self.current_grid} -> {dt_gird}, 资金: {self.available_amount} + {self.position_value} ="
        #       f" {self.available_amount + self.position_value} , {si} {order.amount}")
        order.order_time = market_data.timestamp
        return order

    def handle_position(self, order: Order):
        self.current_grid = order.extend
        # si = "卖" if self.direction != order.side else "买"
        # print(
        #     f"网格购买成功 -> {order.extend}, 资金: {self.available_amount} + {self.position_value} ="
        #     f" {self.available_amount + self.position_value} , {si} {order.amount}")
        self.notify(f"持仓更新: 总投入{self.total_amount} 方向{self.direction} 剩余{self.available_amount}"
                    f" 网格数{self.current_grid}/{self.grid} 持仓数量：{self.position_map[self.symbol].quantity}")

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
