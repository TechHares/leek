#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:59
# @Author  : shenglin.li
# @File    : strategy_old.py
# @Software: PyCharm
import json
import os
import re
from abc import abstractmethod, ABCMeta
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict

from leek.common import logger, G
from leek.common.event import EventBus
from leek.common.utils import decimal_quantize, get_defined_classes, all_constructor_args, get_defined_classes_in_file, \
    get_all_base_classes
from leek.strategy.common import Filter
from leek.trade.trade import Order, PositionSide, OrderType as OT


class Position:
    """
    头寸: 持仓信息
    """

    def __init__(self, symbol, direction: PositionSide):
        self.symbol = symbol
        self.direction = direction  # 持仓仓位方向

        self.quantity = Decimal("0")  # 持仓数量
        self.quantity_amount = Decimal("0")  # 花费本金/保证金
        self.avg_price = Decimal("0")  # 平均持仓价格
        self.value = Decimal("0")  # 价值
        self.fee = Decimal("0")  # 手续费消耗

        self.sz = 0

    def update_price(self, price: Decimal):
        if self.direction == PositionSide.LONG:
            self.value = self.quantity_amount + self.quantity * (price - self.avg_price)
        else:
            self.value = self.quantity_amount + self.quantity * (self.avg_price - price)

    def update_filled_position(self, order: Order):
        pre = self.quantity_amount
        self.fee += order.fee
        if self.quantity == 0:
            self.avg_price = order.transaction_price
        profit = Decimal(0)

        if self.direction == order.side:
            self.sz += order.sz
            self.quantity += order.transaction_volume
            self.quantity_amount += order.transaction_amount
        else:
            self.sz -= order.sz
            self.quantity -= order.transaction_volume
            profit = (order.transaction_price - self.avg_price) * order.transaction_volume
            if self.direction == PositionSide.SHORT:
                profit *= -1
            if self.sz == 0:
                self.quantity_amount = Decimal("0")
            else:
                self.quantity_amount -= order.transaction_amount

        if self.quantity == 0:
            self.avg_price = Decimal("0")
            self.value = Decimal("0")
        else:
            self.avg_price = decimal_quantize(self.quantity_amount / self.quantity, 8)
        self.update_price(order.transaction_price)
        return pre - self.quantity_amount + profit

    def get_close_order(self, strategy_id, order_id, price: Decimal = None,
                        order_type=OT.MarketOrder,
                        slippage: Decimal = 0.0,
                        slippage_tiers: int = 0,
                        time_in_force: int = 0):
        """
        获得平仓指令
        :param strategy_id: 策略
        :param order_id: 订单ID
        :param order_type: 订单类型
        :param price: 价格，有价格使用限价单， 无价格使用市价单
        :param slippage: 滑点百分比（滑点最大档位 取小）
        :param slippage_tiers: 滑点最大档位 （滑点百分比 取小）
        :param time_in_force: 滑点触发时间
        :return: 交易指令
        """
        order = Order(strategy_id, order_id, order_type, self.symbol, self.value,
                      price, PositionSide.switch_side(self.direction))
        order.sz = self.sz
        return order

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "quantity": self.quantity.__str__(),
            "quantity_amount": self.quantity_amount.__str__(),
            "avg_price": self.avg_price.__str__(),
            "value": self.value.__str__(),
            "fee": self.fee.__str__()
        }

    @staticmethod
    def form_dict(d):
        position = Position(d["symbol"], PositionSide(d["direction"]))
        if "quantity" in d:
            position.quantity = Decimal(d["quantity"])

        if "quantity_amount" in d:
            position.quantity_amount = Decimal(d["quantity_amount"])

        if "avg_price" in d:
            position.avg_price = Decimal(d["avg_price"])

        if "fee" in d:
            position.fee = Decimal(d["fee"])

        if "value" in d:
            position.value = Decimal(d["value"])

        return position

    def __str__(self):
        return f"Position(symbol={self.symbol}, direction={self.direction}, quantity={self.quantity}, " \
               f"avg_price={self.avg_price}, value={self.value}, fee={self.fee},quantity_amount={self.quantity_amount})"


class PositionManager:
    """
    仓位管理
    """

    def __init__(self, bus: EventBus, total_amount: Decimal):
        self.bus = bus  # 总投入
        self.total_amount = Decimal(total_amount)  # 总投入
        if not total_amount or self.total_amount <= 0:
            raise ValueError("total_amount must > 0")
        self.available_amount = self.total_amount  # 剩余可用

        self.position_value = Decimal("0")  # 持仓价值
        self.fee = Decimal("0")  # 花费手续费
        self.quantity_map: Dict[str, Position] = {}

        self.__seq_id = 0
        self.post_constructor()

    def post_constructor(self):
        """
        订阅相关主题
        """
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.tick_data_handle)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.position_handle)
        self.bus.subscribe(EventBus.TOPIC_STRATEGY_SIGNAL, self.position_signal)

    def tick_data_handle(self, data: G):
        # 1. 更新持仓价值
        if data.symbol in self.quantity_map and data.finish == 1:
            price = data.close
            self.quantity_map[data.symbol].update_price(price)
            self.position_value = sum([position.value for position in self.quantity_map.values()])

    def position_handle(self, order: Order):
        """
        更新持仓
        :param order: 订单指令结果
        """
        logger.info(f"持仓更新: {order}")
        if order.symbol not in self.quantity_map:
            self.quantity_map[order.symbol] = Position(order.symbol, order.side)

        position = self.quantity_map[order.symbol]
        amt = position.update_filled_position(order)
        self.position_value = sum([p.value for p in self.quantity_map.values()])
        # 更新可用资金
        self.available_amount += amt
        if position.quantity == 0:
            del self.quantity_map[order.symbol]
        self.available_amount += order.fee
        self.fee += order.fee
        self.bus.publish("position_update", position, order)
        logger.info(f"已花费手续费: {self.fee}, 可用资金: {self.available_amount}, 仓位价值: {self.position_value}")

    def position_signal(self, signal):
        amount = decimal_quantize((self.available_amount + self.position_value) * signal.position_rate, 2)
        amount = min(amount, self.available_amount)
        logger.info(f"处理策略信号: {signal.symbol}-{signal.signal_name}/{datetime.fromtimestamp(signal.timestamp/1000)}"
                    f" rate={signal.position_rate}, cls={signal.creator.__name__}, price={signal.price}: {signal.memo}")
        if amount <= 0:
            return
        self.__seq_id += 1
        order = Order(signal.strategy_id,
                      f"{signal.strategy_id}{'LONG' if signal.side == PositionSide.LONG else 'SHORT'}{self.__seq_id}",
                      OT.MarketOrder, signal.symbol, amount, signal.price, signal.side, signal.timestamp)
        if signal.signal_type == "CLOSE":
            order.sz = self.get_position(signal.symbol).sz
        order.extend = signal.extend
        self.bus.publish(EventBus.TOPIC_ORDER_DATA, order)

    def get_position(self, symbol) -> Position:
        if symbol in self.quantity_map:
            return self.quantity_map[symbol]

    def get_profit_rate(self, market_data):
        position = self.get_position(market_data.symbol)
        rate = (position.avg_price - market_data.close) / position.avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1
        return rate


class BaseStrategy(metaclass=ABCMeta):
    """
    策略基类， 实现abc方法可快速接入流程
    """

    @abstractmethod
    def __init__(self, strategy_id, bus: EventBus, total_amount: Decimal):
        self.bus = bus
        self.position_manager = PositionManager(bus, total_amount)

        # base 内部变量
        self.__strategy_id = strategy_id
        self.__seq_id = 0
        self.__g_map: Dict[str, G] = {}  # 保存不同标的变量

        # 当前标的策略上文变量
        self.g: G = None  # 任意信息容器
        self.position: Position = None  # 持仓信息asd
        self.market_data = None  # 当前数据

        self.post_constructor()

    def post_constructor(self):
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self._wrap_handle)

    def _wrap_handle(self, market_data: G):
        self.market_data = market_data
        if market_data.symbol not in self.__g_map:
            self.__g_map[market_data.symbol] = G()
        self.g = self.__g_map[market_data.symbol]
        self.position = self.position_manager.get_position(symbol=market_data.symbol)

        classes = get_all_base_classes(self.__class__)
        for bcls in classes:
            if issubclass(bcls, Filter):
                if not bcls.pre(self, market_data, self.position):
                    return
        self.handle()

    @abstractmethod
    def handle(self):
        """
        处理市场数据
        """
        pass

    def _get_seq_id(self):
        self.__seq_id += 1
        return self.__seq_id

    def shutdown(self):
        pass

    def to_dict(self):
        return {
            "运行状态保存": "敬请期待",
        }

    def set_dict_data(self, data):
        pass

    def notify(self, msg):
        self.bus.publish(EventBus.TOPIC_NOTIFY, msg)

    def create_order(self, side: PositionSide, position_rate="0.5", memo="", extend=None):
        """
        创建订单
        :param side: 方向
        :param position_rate: 仓位
        :param memo: 备注
        :param extend: 扩展数据
        """
        position_signal = G()
        position_signal.signal_name = "OPEN_" + ("LONG" if side == PositionSide.LONG else "SHORT")
        position_signal.signal_type = "OPEN"
        position_signal.symbol = self.market_data.symbol
        position_signal.price = self.market_data.close
        position_signal.side = side
        position_signal.timestamp = self.market_data.timestamp
        position_signal.position_rate = Decimal(position_rate)
        position_signal.creator = self.__class__
        position_signal.strategy_id = self.__strategy_id
        position_signal.memo = memo
        position_signal.extend = extend
        self.bus.publish(EventBus.TOPIC_STRATEGY_SIGNAL, position_signal)

    def have_position(self):
        return self.position is not None

    def close_position(self, memo="", extend=None):
        """
        平仓指令
        :return: 交易指令
        """
        position_signal = G()
        position_signal.signal_name = "CLOSE_" + ("LONG" if self.position.direction == PositionSide.LONG else "SHORT")
        position_signal.signal_type = "CLOSE"
        position_signal.symbol = self.market_data.symbol
        position_signal.side = PositionSide.switch_side(self.position.direction)
        position_signal.position_rate = Decimal("1")
        position_signal.price = self.market_data.close
        position_signal.creator = self.__class__
        position_signal.strategy_id = self.__strategy_id
        position_signal.timestamp = self.market_data.timestamp
        position_signal.memo = memo
        position_signal.extend = extend
        self.bus.publish(EventBus.TOPIC_STRATEGY_SIGNAL, position_signal)

    def is_long_position(self):
        return self.position.direction == PositionSide.LONG


def get_all_strategies_cls_iter():
    files = [f for f in os.listdir(Path(__file__).parent)
             if f.endswith(".py") and f not in ["__init__.py", "base.py"]]
    classes = []
    for f in files:
        classes.extend(get_defined_classes(f"leek.strategy.{f[:-3]}"))
    base = BaseStrategy
    if __name__ == "__main__":
        base = get_defined_classes("leek.strategy.base", ["leek.strategy.base.Position"])[0]
    for cls in [cls for cls in classes if issubclass(cls, base)]:
        c = re.findall(r"^<(.*?) '(.*?)'>$", str(cls), re.S)[0][1]
        cls_idx = c.rindex(".")
        desc = (c[:cls_idx] + "|" + c[cls_idx + 1:], c[cls_idx + 1:])
        if hasattr(cls, "verbose_name"):
            desc = (desc[0], cls.verbose_name)
        yield desc


if __name__ == '__main__':
    print([i for i in get_all_strategies_cls_iter()])
    # position = Position("SDT", PositionSide.LONG)
    # print(json.dumps(position.to_dict()))
    #
    # form_dict = Position.form_dict(
    #     {"symbol": "ETH-USDT-SWAP", "direction": 2, "quantity": "0.78", "quantity_amount": "695.78",
    #      "avg_price": "2676.08000000", "value": "696.2714000000", "fee": "-1.0436712"})
    # # form_dict.update_price(Decimal("2679.11"))
    # form_dict.update_price(Decimal("2671.76"))
    # # 2.37
    # print(form_dict.value + form_dict.fee - form_dict.quantity_amount)
