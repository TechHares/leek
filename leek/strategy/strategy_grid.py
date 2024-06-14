#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:47
# @Author  : shenglin.li
# @File    : strategy_grid.py
# @Software: PyCharm

from leek.common import EventBus, logger
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
        self.threshold = 60  # 定义暴力波动阈值 x秒内穿多个网格
        self.current_grid = Decimal("0")
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
            if self.g.order_time is None and self.current_grid > 0:  # 有持仓
                self.g.order_time = int(datetime.now().timestamp())
                self.notify(f"SingleGridStrategy {market_data.symbol}价格{price}超出风控范围{self.min_price * (1 - self.risk_rate)}"
                            f"-{self.max_price * (1 + self.risk_rate)} 平仓")
                self.g.gird = -self.current_grid
                self.close_position("网格风控")
                self.risk = True
            return
        if self.is_long():
            dt_price = self.max_price - price
        else:
            dt_price = price - self.min_price

        self.add_position(dt_price)
        if self.have_position():
            self.sub_position(dt_price)

    def sub_position(self, dt_price):
        if self.g.order_time is not None:
            if int(datetime.now().timestamp()) > self.g.order_time + 120:
                logger.error(f"订单一直没处理完")
            return
        price = self.market_data.close
        dt_gird = max(decimal_quantize(dt_price / self.grid_price, 0, 1), 0)
        if dt_gird >= self.current_grid or (dt_gird == 0 and self.current_grid == 1):
            return

        if self.g.last_sub_time and int(datetime.now().timestamp()) - self.g.last_sub_time < self.threshold:  # 暴力下杀先避开
            return

        rate = abs(self.current_grid - dt_gird) / self.grid
        logger.info(
            f"方向{self.side} "
            f" 网格数{self.current_grid}/{self.grid} 平仓：{rate}\n"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{dt_gird}\n"
        )
        self.g.gird = -abs(self.current_grid - dt_gird)
        self.g.order_time = int(datetime.now().timestamp())
        self.g.last_sub_time = int(datetime.now().timestamp())
        self.g.last_add_time = None
        self.close_position(rate=rate)

    def add_position(self, dt_price):
        if self.g.order_time is not None:
            if int(datetime.now().timestamp()) > self.g.order_time + 120:
                logger.error(f"订单一直没处理完")
            return
        price = self.market_data.close
        if price > self.max_price or price < self.min_price:
            return
        dt_gird = min(self.grid, decimal_quantize(dt_price / self.grid_price, 0, 2))  # 防止风控设置过大导致超出网格个数
        if dt_gird <= self.current_grid:
            return
        if self.risk:  # 已经风控
            if dt_gird > self.grid - 2:
                return
            self.risk = False
        if self.g.last_add_time and int(datetime.now().timestamp()) - self.g.last_add_time < self.threshold:  # 暴力拉升先避开
            return
        side = PS.LONG if self.is_long() else PS.SHORT
        rate = abs(self.current_grid - dt_gird) / self.grid
        logger.info(
            f"方向{self.side} 操作方向{side}"
            f" 网格数{self.current_grid}/{self.grid} 加仓：{rate}\n"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{dt_gird}\n"
        )
        self.g.gird = abs(self.current_grid - dt_gird)
        self.g.order_time = int(datetime.now().timestamp())
        self.g.last_add_time = int(datetime.now().timestamp())
        self.g.last_sub_time = None
        self.create_order(side, rate)

    def handle_position(self, order):
        self.current_grid += self.g.gird
        self.g.order_time = None
        si = "卖" if self.side != order.side else "买"
        logger.info(
            f"网格购买成功 {self.g.gird} -> {self.current_grid}, 资金: {self.position_manager.available_amount} + {self.position_manager.position_value} ="
            f" {self.position_manager.available_amount + self.position_manager.position_value} , {si} {order.amount}")
        self.g.gird = 0

    def to_dict(self):
        d = super().to_dict()
        d["risk"] = self.risk
        return d

    def set_dict_data(self, data):
        super().set_dict_data(data)

        if "risk" in data:
            self.risk = data["risk"]


if __name__ == '__main__':
    pass
