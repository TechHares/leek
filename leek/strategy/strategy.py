#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:59
# @Author  : shenglin.li
# @File    : strategy.py
# @Software: PyCharm
import json
import os
import re
from abc import abstractmethod, ABCMeta
from decimal import Decimal
from pathlib import Path
from typing import Dict

from leek.common import logger, G
from leek.common.event import EventBus
from leek.common.utils import decimal_quantize, get_defined_classes, all_constructor_args, get_defined_classes_in_file, \
    get_all_base_classes
from leek.trade.trade import Order, PositionSide, OrderType as OT


class Position:
    """
    头寸: 持仓信息
    """

    def __init__(self, symbol, direction: PositionSide):
        self.symbol = symbol
        self.direction = direction  # 持仓仓位方向

        self.quantity = Decimal("0")  # 持仓数量
        self.quantity_amount = Decimal("0")  # 花费本金
        self.avg_price = Decimal("0")  # 平均持仓价格
        self.value = Decimal("0")  # 价值
        self.fee = Decimal("0")  # 手续费消耗

        self.sz = 0
        self.win = False

    def update_price(self, price: Decimal):
        if self.direction == PositionSide.LONG:
            self.value = self.quantity * price
        else:
            self.value = self.quantity_amount + self.quantity * (self.avg_price - price)

    def trade_result(self, order: Order):
        return (self.direction != order.side) \
               and (
                       (self.direction == PositionSide.LONG and order.transaction_price > self.avg_price)
                       or
                       (self.direction == PositionSide.SHORT and order.transaction_price < self.avg_price)
               )

    def update_filled_position(self, order: Order):
        self.fee += order.fee
        pre_value = self.avg_price * self.quantity
        self.win = self.trade_result(order)

        if self.direction == order.side:
            self.sz += order.sz
            self.quantity_amount += order.transaction_amount
        else:
            self.quantity_amount -= order.transaction_amount
            self.sz -= order.sz
        self.quantity = self.sz * order.cct
        if self.quantity == 0:
            self.avg_price = Decimal("0")
            self.value = Decimal("0")
        else:
            self.avg_price = decimal_quantize((pre_value + order.transaction_volume * order.transaction_price)
                                              / self.quantity, 8)
        self.update_price(order.transaction_price)

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


class BaseStrategy(metaclass=ABCMeta):
    """
    策略基类， 实现abc方法可快速接入流程
    """

    @abstractmethod
    def __init__(self, job_id, bus: EventBus, total_amount: Decimal):
        self.total_amount = Decimal(total_amount)  # 总投入
        if not total_amount or total_amount <= 0:
            raise ValueError("total_amount must > 0")
        self.available_amount = self.total_amount  # 剩余可用
        self.position_value = Decimal("0")  # 持仓价值
        self.bus = bus
        self.fee = Decimal("0")
        self.job_id = job_id
        self.__seq_id = 0
        self.position_map: Dict[str, Position] = {}
        self.g_map: Dict[str, G] = {}
        self.g: G = None

    @abstractmethod
    def handle(self, market_data: G) -> Order:
        """
        处理市场数据
        :param market_data: 字典类型 key参见 1-2.custom-data-source.md
        :return: 返回交易指令 无变化None
        """
        if market_data.symbol not in self.g_map:
            self.g_map[market_data.symbol] = G()
        self.g = self.g_map[market_data.symbol]
        if market_data.symbol in self.position_map and market_data.finish == 1:
            price = market_data.close
            self.position_map[market_data.symbol].update_price(price)
            # 更新持仓价值
            self.position_value = sum([position.value for position in self.position_map.values()])

    def _get_seq_id(self):
        self.__seq_id += 1
        return self.__seq_id

    def training(self, *datas):
        """
        训练
        :param datas: 数据
        """
        pass

    def handle_position(self, order: Order):
        """
        更新持仓
        :param order: 订单指令结果
        """
        logger.info(f"持仓更新: {order}")
        if order.symbol not in self.position_map:
            self.position_map[order.symbol] = Position(order.symbol, order.side)

        position = self.position_map[order.symbol]
        position.update_filled_position(order)
        self.position_value = sum([p.value for p in self.position_map.values()])
        # 更新可用资金
        if position.direction == order.side:
            self.available_amount -= order.transaction_amount
        else:
            self.available_amount += order.transaction_amount
        if position.quantity == 0:
            del self.position_map[order.symbol]
        self.available_amount += order.fee
        self.fee += order.fee
        self.bus.publish("position_update", position, order)

    def shutdown(self):
        pass

    def to_dict(self):
        return {
            "available_amount": self.available_amount.__str__(),
            "position_value": self.position_value.__str__(),
            "fee": self.fee.__str__(),
            "__seq_id": self.__seq_id,
            "profit": (self.position_value + self.available_amount - self.total_amount + self.fee).__str__(),
            "position_map": {k: v.to_dict() for k, v in self.position_map.items()},
        }

    def set_dict_data(self, data):
        if "available_amount" in data:
            self.available_amount = Decimal(data["available_amount"])
        if "position_value" in data:
            self.position_value = Decimal(data["position_value"])
        if "fee" in data:
            self.fee = Decimal(data["fee"])
        if "__seq_id" in data:
            self.__seq_id = data["__seq_id"]
        if "position_map" in data:
            self.position_map = {k: Position.form_dict(v) for k, v in data["position_map"].items()}

    def notify(self, msg):
        self.bus.publish(EventBus.TOPIC_NOTIFY, msg)

    def get_position(self, market_data: G) -> Position:
        if self.have_position(market_data):
            return self.position_map[market_data.symbol]
        return None

    def have_position(self, market_data: G) -> bool:
        """
        是否有持仓
        """
        return market_data.symbol in self.position_map

    def position_is_long(self, market_data: G) -> bool:
        """
        持仓为多？
        :return: True 多 False 空
        """
        return self.position_map[market_data.symbol].direction == PositionSide.LONG

    def _create_order(self, market_data: G, side: PositionSide, amount: Decimal, tp: OT = OT.MarketOrder) -> Order:
        """
        创建订单
        :param market_data: 市场数据
        :param side: 方向
        :param amount: 数量
        :param tp: 订单类型
        """
        order = Order(self.job_id, f"OPEN{self.job_id}{self._get_seq_id()}", tp, market_data.symbol)
        order.side = side
        order.amount = amount
        order.price = market_data.close
        order.order_time = market_data.timestamp
        return order

    def _close_position(self, market_data: G) -> Order:
        """
        获得平仓指令
        :param market_data: 市场数据
        :return: 交易指令
        """
        return self.position_map[market_data.symbol].get_close_order(self.job_id, f"CLOSE{self.job_id}{self._get_seq_id()}", market_data.close)


def get_all_strategies_cls_iter():
    files = [f for f in os.listdir(Path(__file__).parent)
             if f.endswith(".py") and f not in ["__init__.py", "strategy.py", "strategy_common.py"]]
    classes = []
    for f in files:
        classes.extend(get_defined_classes(f"leek.strategy.{f[:-3]}"))
    base = BaseStrategy
    if __name__ == "__main__":
        base = get_defined_classes("leek.strategy.strategy", ["leek.strategy.strategy.Position"])[0]
    for cls in [cls for cls in classes if issubclass(cls, base)]:
        c = re.findall(r"^<(.*?) '(.*?)'>$", str(cls), re.S)[0][1]
        cls_idx = c.rindex(".")
        desc = (c[:cls_idx] + "|" + c[cls_idx+1:], c[cls_idx+1:])
        if hasattr(cls, "verbose_name"):
            desc = (desc[0], cls.verbose_name)
        yield desc


if __name__ == '__main__':
    print(get_all_strategies_cls_iter())
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
