#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 15:47
# @Author  : shenglin.li
# @File    : strategy_grid.py
# @Software: PyCharm

from leek.common import EventBus, logger
from leek.common.utils import *
from leek.strategy import BaseStrategy
from leek.strategy.common import *
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.t import RSI, StochRSI
from leek.trade.trade import PositionSide as PS, PositionSide


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
        self.threshold = 60 * 1000  # 定义暴力波动阈值 x豪秒内穿多个网格
        self.current_grid = Decimal("0")
        self.risk = False  # 是否已经风控

    def post_constructor(self):
        super().post_constructor()
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA_AFTER, self.handle_position)

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
        if self.have_position() and self.side != self.position.direction:
            self.g.order_time = int(datetime.now().timestamp())
            logger.error(
                f"SingleGridStrategy {market_data.symbol}持仓与目标方向相反，平仓")
            self.g.gird = -self.current_grid
            self.close_position("平仓")
            return

        if price > self.max_price * (1 + self.risk_rate) or price < self.min_price * (1 - self.risk_rate):
            if self.g.order_time is None and self.current_grid > 0:  # 有持仓
                self.g.order_time = int(datetime.now().timestamp())
                logger.error(
                    f"SingleGridStrategy {market_data.symbol}价格{price}超出风控范围{self.min_price * (1 - self.risk_rate)}"
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
            logger.debug(f"订单进行中放弃减仓, 订单时间: {DateTime.to_date_str(self.g.order_time)}")
            return
        price = self.market_data.close
        dt_gird = max(decimal_quantize(dt_price / self.grid_price, 0, 1), 0)
        if dt_gird >= self.current_grid or (dt_gird == 0 and self.current_grid == 1):
            logger.debug(f"无需减仓: {dt_gird} / {self.current_grid}")
            return

        if self.g.last_sub_time and self.market_data.current_time - self.g.last_sub_time < self.threshold:  # 暴力下杀先避开
            logger.debug(f"遭遇暴力波动放弃减仓: {DateTime.to_date_str(self.g.last_sub_time)} "
                         f"{DateTime.to_date_str(self.market_data.current_time)} {self.threshold}")
            return

        rate = abs(self.current_grid - dt_gird) / self.grid
        logger.info(
            f"方向{self.side} "
            f" 网格数{self.current_grid}/{self.grid} 平仓：{rate}"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{dt_gird}"
        )
        self.g.gird = -abs(self.current_grid - dt_gird)
        self.g.order_time = self.market_data.current_time
        self.g.last_sub_time = self.market_data.current_time
        self.g.last_add_time = None
        self.close_position(rate=rate)

    def add_position(self, dt_price):
        if self.g.order_time is not None:
            if int(datetime.now().timestamp() * 1000) > self.g.order_time + 120000:
                logger.error(f"订单一直没处理完")
            logger.debug(f"订单进行中放弃加仓, 订单时间: {DateTime.to_date_str(self.g.order_time)}")
            return
        price = self.market_data.close
        if price > self.max_price or price < self.min_price:
            logger.debug(f"价格超出网格放弃加仓: {self.min_price}~{self.max_price} 当前{price}")
            return
        target_gird = min(self.grid, decimal_quantize(dt_price / self.grid_price, 0, 2))  # 防止风控设置过大导致超出网格个数
        if target_gird <= self.current_grid:
            logger.debug(f"无需加仓: {target_gird} / {self.current_grid}")
            return
        if self.risk:  # 已经风控
            if target_gird > self.grid - 2:
                return
            self.risk = False
        if self.g.last_add_time and int(
                datetime.now().timestamp() * 1000) - self.g.last_add_time < self.threshold:  # 暴力拉升先避开
            logger.debug(f"遭遇暴力波动放弃加仓: {DateTime.to_date_str(self.g.last_add_time)} {self.threshold}")
            return
        side = PS.LONG if self.is_long() else PS.SHORT
        rate = abs(self.current_grid - target_gird) / self.grid
        logger.info(
            f"方向{self.side} 操作方向{side}"
            f" 网格数{self.current_grid}/{self.grid} 加仓：{rate}"
            f"价格区间{self.min_price}-{self.max_price} 当前价格{price} 应持仓层数{target_gird}"
        )
        self.g.gird = abs(self.current_grid - target_gird)
        self.g.order_time = self.market_data.current_time
        self.g.last_add_time = self.market_data.current_time
        self.g.last_sub_time = None
        self.create_order(side, rate)

    def handle_position(self, order):
        if order.transaction_volume > 0:
            self.current_grid += self.g.gird
        self.g.order_time = None
        si = "卖" if self.side != order.side else "买"
        logger.info(
            f"网格购买成功 {self.g.gird} -> {self.current_grid}, 资金: {self.position_manager.available_amount} + {self.position_manager.position_value} ="
            f" {self.position_manager.available_amount + self.position_manager.position_value} , {si} {order.amount}")
        self.g.gird = 0

    def marshal(self):
        d = super().marshal()
        d["risk"] = self.risk
        d["current_grid"] = "%s" % self.current_grid
        return d

    def unmarshal(self, data):
        super().unmarshal(data)

        if "risk" in data:
            self.risk = data["risk"]
        if "current_grid" in data:
            self.current_grid = Decimal(data["current_grid"])


    def single_ignore(self, single):
        self.g.order_time = None


class RSIGridStrategy(SingleGridStrategy):
    verbose_name = "RSI网格"
    release = True

    def __init__(self, over_buy=80, over_sell=20):
        self.rsi = StochRSI()
        self.over_sell = int(over_sell)
        self.over_buy = int(over_buy)

        self.k = None
        self.d = None

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 50
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.rsi.update(market_data)
        logger.info(f"RSI数据初始化完成")

    def handle(self):
        self.k, self.d = self.rsi.update(self.market_data)
        self.market_data.k = self.k
        self.market_data.d = self.d
        logger.debug(f"RSI网格 {self.k} {self.d} {self.market_data}")
        super().handle()

    def add_position(self, dt_price):
        if self.can(self.side):
            super().add_position(dt_price)
        else:
            logger.debug(f"{self.side}方向RSI未到条件 不加仓")

    def sub_position(self, dt_price):
        if self.can(self.side.switch()):
            super().sub_position(dt_price)
        else:
            logger.debug(f"{self.side}方向RSI未到条件 不加仓")

    def can(self, side: PS):
        if self.k is None or self.d is None:
            return False
        if side == PS.LONG:
            return self.d < self.k < self.over_sell
        else:
            return self.d > self.k > self.over_buy


class RSIGridStrategyV2(RSIGridStrategy):
    verbose_name = "RSI网格V2"
    release = True

    def __init__(self, limit_threshold=3):
        self.limit_threshold = int(limit_threshold)

    def create_order(self, side: PositionSide, position_rate="0.5", memo="", extend=None):
        logger.debug(f"RSIGridStrategyV2 加仓， 清除平仓阈值")
        self.g.limit = 0
        super(RSIGridStrategyV2, self).create_order(side, position_rate, memo, extend)

    def close_position(self, memo="", extend=None, rate="1"):
        self.g.limit += 1
        logger.debug(f"RSIGridStrategyV2 平仓， 连续平仓次数 {self.g.limit}")
        if self.g.limit >= self.limit_threshold:
            logger.info(f"RSIGridStrategyV2 连续平仓次数达到阈值， 全平")
            self.g.gird = -self.current_grid
            rate = "1"
        super(RSIGridStrategyV2, self).close_position(memo, extend, rate=rate)
        self.risk = False

    def marshal(self):
        marshal = RSIGridStrategy.marshal(self)
        g = {}
        for k in self.g_map:
            g[k] = self.g_map[k].limit
        marshal["g_map"] = g
        return marshal

    def unmarshal(self, data):
        RSIGridStrategy.unmarshal(self, data)
        if "g_map" in data:
            for k, v in data["g_map"].items():
                self.g_map[k].limit = int(v)


if __name__ == '__main__':
    pass
