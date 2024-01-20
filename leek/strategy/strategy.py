#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:59
# @Author  : shenglin.li
# @File    : strategy.py
# @Software: PyCharm
import json
from abc import abstractmethod, ABCMeta
from decimal import Decimal
from typing import Dict

from leek.common import logger
from leek.common.event import EventBus
from leek.common.utils import decimal_quantize
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

    def update_price(self, price: Decimal):
        if self.direction == PositionSide.LONG:
            self.value = self.quantity * price
        else:
            self.value = self.quantity_amount + self.quantity * (self.avg_price - price)

    def update_filled_position(self, order: Order):
        self.fee += order.fee
        pre_value = self.avg_price * self.quantity
        if self.direction == order.side:
            self.quantity += order.transaction_volume
            self.quantity_amount += order.transaction_amount
        else:
            self.quantity -= order.transaction_volume
            self.quantity_amount -= order.transaction_amount
        if self.quantity == 0:
            self.avg_price = Decimal("0")
            self.value = Decimal("0")
        else:
            self.avg_price = decimal_quantize((pre_value + order.transaction_volume * order.transaction_price)
                                              / self.quantity, 8)
        self.update_price(order.transaction_price)

    def get_close_order(self, strategy_id, order_id, price: Decimal = None, slippage: Decimal = 0.0,
                        slippage_tiers: int = 0,
                        time_in_force: int = 0):
        """
        获得平仓指令
        :param strategy_id: 策略
        :param order_id: 订单ID
        :param price: 价格，有价格使用限价单， 无价格使用市价单
        :param slippage: 滑点百分比（滑点最大档位 取小）
        :param slippage_tiers: 滑点最大档位 （滑点百分比 取小）
        :param time_in_force: 滑点触发时间
        :return: 交易指令
        """
        order = Order(strategy_id, order_id, OT.LimitOrder, self.symbol, self.value,
                      price, PositionSide.switch_side(self.direction))
        if not price:
            order.type = OT.MarketOrder
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
    def __init__(self, job_id, bus: EventBus, total_amount: Decimal, available_amount: Decimal = None,
                 position_value: Decimal = None):
        self.total_amount = Decimal(total_amount)  # 总投入
        if not total_amount or total_amount <= 0:
            raise ValueError("total_amount must > 0")
        if not available_amount:
            available_amount = self.total_amount
        self.available_amount = Decimal(available_amount)  # 剩余可用
        if not position_value:
            position_value = Decimal("0")
        self.position_value = position_value  # 持仓价值
        self.bus = bus
        self.fee = Decimal("0")
        self.job_id = job_id
        self.__seq_id = 0
        self.position_map: Dict[str, Position] = {}

    @abstractmethod
    def handle(self, market_data: Dict) -> Order:
        """
        处理市场数据
        :param market_data: 字典类型 key参见 market_data.md
        :return: 返回交易指令 无变化None
        """
        if market_data["symbol"] in self.position_map and market_data["finish"] == 1:
            price = market_data["close"]
            self.position_map[market_data["symbol"]].update_price(price)
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

        self.position_map[order.symbol].update_filled_position(order)
        self.position_value = sum([position.value for position in self.position_map.values()])
        # 更新可用资金
        if self.position_map[order.symbol].direction == order.side:
            self.available_amount -= order.transaction_amount
        else:
            self.available_amount += order.transaction_amount
        self.available_amount += order.fee
        self.fee += order.fee

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


if __name__ == '__main__':
    position = Position("SDT", PositionSide.LONG)
    print(json.dumps(position.to_dict()))

    form_dict = Position.form_dict({"symbol": "ETH-USDT-SWAP", "direction": 2, "quantity": "0.78", "quantity_amount": "695.78", "avg_price": "2676.08000000", "value": "696.2714000000", "fee": "-1.0436712"})
    # form_dict.update_price(Decimal("2679.11"))
    form_dict.update_price(Decimal("2671.76"))
    # 2.37
    print(form_dict.value + form_dict.fee - form_dict.quantity_amount)



