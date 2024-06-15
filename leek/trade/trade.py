#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 20:01
# @Author  : shenglin.li
# @File    : trade.py
# @Software: PyCharm
import inspect
import os
import re
import time
from datetime import datetime
from abc import abstractmethod, ABCMeta
from decimal import Decimal
from enum import Enum
from pathlib import Path

import cachetools

from leek.common import EventBus
from leek.common.utils import get_defined_classes


class PositionSide(Enum):
    """
    头寸方向 PositionSide
    """
    LONG = 1  # 多头
    SHORT = 2  # 空头
    FLAT = 4  # 多/空头

    @staticmethod
    def switch_side(side):
        if side == PositionSide.LONG:
            return PositionSide.SHORT
        if side == PositionSide.SHORT:
            return PositionSide.LONG
        raise RuntimeError

    def switch(self):
        return self.switch_side(self)

    def is_long(self):
        return self == PositionSide.LONG


class OrderType(Enum):
    """
    交易类型 OrderType
    """
    MarketOrder = 1  # 市价单
    LimitOrder = 2  # 限价单


class TradeMode(Enum):
    """
    交易模式
    """
    ISOLATED = 1  # 保证金模式-逐仓
    CROSS = 2  # 保证金模式-全仓
    CASH = 3  # 非保证金模式-非保证金


class TradeInsType(Enum):
    """
    交易产品类型
    """

    SPOT = 1  # 现货
    MARGIN = 2  # 杠杆
    SWAP = 3  # 合约
    FUTURES = 4  # 期货
    OPTION = 5  # 期权


class Order:
    """
    交易指令
    """

    def __init__(self, strategy_id: str, order_id, tp: OrderType, symbol: str, amount: Decimal = 0.0,
                 vol: Decimal = 0.0, price: Decimal = None, side: PositionSide = PositionSide.LONG,
                 order_time: datetime = None, trade_ins_type: TradeInsType = TradeInsType.SWAP,
                 trade_mode: TradeMode = TradeMode.ISOLATED, sz=None, pos_type=None, lever=1):
        self.strategy_id = strategy_id  # 策略ID
        self.order_id = order_id  # 订单ID
        self.trade_ins_type = trade_ins_type  # 交易标的类型
        self.type = tp  # 类型
        self.trade_mode = trade_mode  # 交易类型 保证金模式：isolated：逐仓 ；cross：全仓 ； 非保证金模式：cash：非保证金
        self.symbol = symbol  # 产品
        self.price = price  # 价格
        self.amount = amount  # 报单额
        self.vol = vol  # 报单数量
        self.side = side  # 交易方向
        self.lever = lever  # 杠杆倍数
        self.order_time = order_time  # 时间
        if self.order_time is None:
            self.order_time = int(time.time()*1000)
        self.pos_type = pos_type

        self.sz = sz  # 实际需交易数量，如amount与实际挂单之间有运算，传此值不转化直接使用
        self.cct = None  # sz 对应面值

        self.transaction_volume = None  # 成交数量
        self.transaction_amount = None  # 成交金额
        self.transaction_price = None  # 成交价格
        self.fee = None  # 费用
        self.extend = None

    def __str__(self):
        return f"Order(strategy={self.strategy_id}, order_id={self.order_id}, type={self.type}, symbol={self.symbol}, " \
               f"price={self.price}, amount={self.amount}, side={self.side}, time={self.order_time}, sz={self.sz}, " \
               f"transaction_volume={self.transaction_volume}, transaction_amount={self.transaction_amount}, " \
               f"transaction_price={self.transaction_price}, fee={self.fee}, extend={self.extend})"


class Trader(metaclass=ABCMeta):
    """
    交易抽象
    """

    def __init__(self, bus: EventBus):
        self.bus = bus

        self.post_constructor()

    def post_constructor(self):
        self.bus.subscribe(EventBus.TOPIC_ORDER_DATA, self.order)

    @abstractmethod
    def order(self, order: Order) -> Order:
        """
        下单
        :param order:
        :return: 订单信息 补全成交相关信息
        """
        raise NotImplemented

    def _trade_callback(self, order):
        """
        交易回调 反馈成交详细等信息
        :param order: 订单
        :return:
        """
        self.bus.publish(EventBus.TOPIC_POSITION_DATA, order)

    def shutdown(self):
        pass


@cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
def get_all_trader_cls_list():
    files = [f for f in os.listdir(Path(__file__).parent)
             if f.endswith(".py") and f not in ["__init__.py", "trade.py"]]
    classes = []
    for f in files:
        classes.extend(get_defined_classes(f"leek.trade.{f[:-3]}"))
    base = Trader
    if __name__ == "__main__":
        base = get_defined_classes("leek.trade.trade", ["leek.trade.trade.PositionSide",
                                                        "leek.trade.trade.OrderType",
                                                        "leek.trade.trade.Order"])[0]
    res = []
    for cls in [cls for cls in classes if issubclass(cls, base) and not inspect.isabstract(cls)]:
        c = re.findall(r"^<(.*?) '(.*?)'>$", str(cls), re.S)[0][1]
        cls_idx = c.rindex(".")
        desc = (c[:cls_idx] + "|" + c[cls_idx + 1:], c[cls_idx + 1:])
        if hasattr(cls, "verbose_name"):
            desc = (desc[0], cls.verbose_name)
        res.append(desc)
    return res


if __name__ == '__main__':
    pass
