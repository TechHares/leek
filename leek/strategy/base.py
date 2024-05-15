#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 16:59
# @Author  : shenglin.li
# @File    : strategy_old.py
# @Software: PyCharm
import inspect
import os
import re
import threading
import time
from abc import abstractmethod, ABCMeta
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict

import cachetools

from leek.common import logger, config, notify
from leek.common import G
from leek.common.event import EventBus
from leek.common.utils import decimal_quantize, get_defined_classes, get_all_base_classes
from leek.strategy.common import Filter
from leek.trade.trade import Order, PositionSide, OrderType as OT


class Position:
    """
    头寸: 持仓信息
    """

    def __init__(self, symbol, direction: PositionSide):
        self.symbol = symbol
        self.direction = direction  # 持仓仓位方向

        self.quantity_rate = Decimal("0")  # 投入仓位比例
        self.quantity_amount = Decimal("0")  # 花费本金/保证金

        self.quantity = Decimal("0")  # 持仓数量
        self.avg_price = Decimal("0")  # 持仓平均价
        self.fee = Decimal("0")  # 费用损耗

        self.value = Decimal("0")  # 仓位价值
        self.cur_price = Decimal("0")  # 当前价格
        self.sz = 0

    def update_price(self, price: Decimal):
        self.cur_price = price
        if self.direction == PositionSide.LONG:
            self.value = self.quantity_amount + (price - self.avg_price) * self.quantity
        else:
            self.value = self.quantity_amount - (price - self.avg_price) * self.quantity

    def update_filled_position(self, order):
        self.fee += abs(order.fee)

        if self.direction == order.side:
            quantity_value = self.avg_price * self.quantity + order.transaction_volume * order.transaction_price
            self.sz += order.sz
            self.quantity += order.transaction_volume
            self.avg_price = decimal_quantize(quantity_value / self.quantity, 8)
            self.quantity_amount += order.transaction_amount
            return_amount = order.transaction_amount
        else:
            if self.direction == PositionSide.LONG:
                return_amount = order.transaction_volume / self.quantity * self.quantity_amount \
                                + (order.transaction_price - self.avg_price) * order.transaction_volume
            else:
                return_amount = order.transaction_volume / self.quantity * self.quantity_amount \
                                + (self.avg_price - order.transaction_price) * order.transaction_volume
            self.sz -= order.sz
            self.quantity -= order.transaction_volume
            self.quantity_amount -= order.transaction_amount
        self.update_price(order.transaction_price)
        # logger.info(f"仓位变动[{self.symbol}] {self.direction} {self.quantity} {self.avg_price} {self.value}")
        return return_amount

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

    def __str__(self):
        return f"Position(symbol={self.symbol}, direction={self.direction},avg_price={self.avg_price}," \
               f"quantity={self.quantity_rate},quantity_amount={self.quantity_amount}, " \
               f"fee={self.fee}," \
               f"quantity={self.quantity} sz={self.sz},cur_price={self.cur_price},value={self.value})"


lock = threading.RLock()


def locked(func):
    def wrapper(*args, **kw):
        with lock:
            return func(*args, **kw)

    return wrapper


class PositionManager:
    """
    仓位管理
    """
    MIN_POSITION = config.MIN_POSITION

    def __init__(self, bus: EventBus, total_amount: Decimal):
        self.bus = bus  # 总投入
        self.total_amount = Decimal(total_amount)  # 总投入
        if not total_amount or self.total_amount <= 0:
            raise ValueError("total_amount must > 0")

        self.available_amount = self.total_amount  # 可用金额
        self.freeze_amount = Decimal("0")  # 冻结金额
        self.used_amount = Decimal("0")  # 已用金额
        self.available_rate = Decimal("1")  # 可用比例
        self.freeze_rate = Decimal("0")  # 冻结比例
        self.used_rate = Decimal("0")  # 已用比例
        self.freeze_map = {}

        self.position_value = Decimal("0")  # 持仓价值
        self.fee = Decimal("0")  # 花费手续费
        self.quantity_map: Dict[str, Position] = {}

        self.__seq_id = 0
        self.post_constructor()
        self.signal_processing_map = {}

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

    @locked
    def position_handle(self, trade):
        """
        更新持仓
        :param trade: 订单指令结果
        """
        # logger.info(f"持仓更新: {order}")
        if trade.symbol not in self.quantity_map:
            self.quantity_map[trade.symbol] = Position(trade.symbol, trade.side)

        position = self.quantity_map[trade.symbol]
        self.logger_print("仓位更新", (trade.__str__(), position.__str__()))
        self.bus.publish(EventBus.TOPIC_POSITION_UPDATE, position, trade)

        amt = position.update_filled_position(trade)
        if position.direction == trade.side:  # 开仓
            rate = self.release_amount(trade.order_id, amt, trade.fee)
            position.quantity_rate += rate
        else:
            self.release_position(position.quantity_rate, amt, trade.fee)

        # 更新可用资金
        if position.quantity == 0:
            del self.quantity_map[trade.symbol]
        del self.signal_processing_map[trade.symbol]
        self.logger_print("仓位更新结束", (trade.__str__(), position.__str__()))

    def logger_print(self, mark, extend=None):
        self.position_value = Decimal(sum([p.value for p in self.quantity_map.values()]))
        a = decimal_quantize(self.available_amount + self.freeze_amount + self.position_value)
        logger.info(f"策略资产[{mark}]: {a}=可用({decimal_quantize(self.available_amount)}/{self.available_rate})"
                    f" + 冻结({decimal_quantize(self.freeze_amount.quantize(2))} / {self.freeze_rate})"
                    f" + 已用({decimal_quantize(self.used_amount)} / {self.used_rate})"
                    f" + 市值({decimal_quantize(self.position_value)}), 已花费手续费: {self.fee}"
                    f"  数据: {extend} ")

    def get_value(self):
        """
        返回当前价值
        :return:
        """
        return decimal_quantize(self.available_amount + self.freeze_amount + self.position_value)

    @locked
    def position_signal(self, signal):
        if signal.symbol in self.signal_processing_map:
            logger.info(f"标的有信号正在处理，忽略: 正在处理订单{self.signal_processing_map[signal.symbol]} => {signal.symbol}"
                        f"-{signal.signal_name}/{datetime.fromtimestamp(signal.timestamp / 1000)}"
                        f" rate={signal.position_rate}, cls={signal.creator.__name__},"
                        f" price={signal.price}: {signal.memo}")
            return
        logger.info(f"处理策略信号: {signal.symbol}-{signal.signal_name}/{datetime.fromtimestamp(signal.timestamp / 1000)}"
                    f" rate={signal.position_rate}, cls={signal.creator.__name__}, price={signal.price}: {signal.memo}")

        self.__seq_id += 1
        order_id = f"{signal.strategy_id}{'LONG' if signal.side == PositionSide.LONG else 'SHORT'}{self.__seq_id}"
        self.signal_processing_map[signal.symbol] = order_id

        order = Order(signal.strategy_id, order_id, OT.MarketOrder, signal.symbol, Decimal(0), signal.price,
                      signal.side, signal.timestamp)

        if signal.signal_type == "CLOSE":
            if self.get_position(signal.symbol).sz is not None:
                order.sz = self.get_position(signal.symbol).sz
        else:
            amount = self.freeze(order_id, signal.position_rate)
            if amount <= 0:
                return
            order.amount = amount

        order.extend = signal.extend
        self.bus.publish(EventBus.TOPIC_ORDER_DATA, order)

    @locked
    def freeze(self, order_id, rate) -> Decimal:
        """
        冻结
        :param order_id: 订单ID
        :param rate: 冻结比例
        :return: 金额
        """
        rate = decimal_quantize(min(rate, self.available_rate), 3)
        if rate < PositionManager.MIN_POSITION:
            return Decimal(0)
        if config.ROLLING_POSITION:
            freeze_amount = min(decimal_quantize(rate / self.available_rate * self.available_amount, 2),
                                self.available_amount)
        else:
            freeze_amount = min(decimal_quantize(rate * self.total_amount, 2), self.available_amount)

        if freeze_amount < PositionManager.MIN_POSITION * self.total_amount < self.available_amount:
            freeze_amount = Decimal(self.available_amount)
        if freeze_amount < PositionManager.MIN_POSITION * self.total_amount:
            return Decimal(0)
        self.available_rate -= rate
        self.available_amount -= freeze_amount

        self.freeze_rate += rate
        self.freeze_amount += freeze_amount

        self.freeze_map[order_id] = [rate, freeze_amount]
        self.logger_print("冻结成功", (order_id, rate))
        return freeze_amount

    @locked
    def release_amount(self, order_id, real_amount, fee=0):
        """
        释放金额
        :param fee: 手续费
        :param order_id: 冻结记录
        :param real_amount: 实际金额
        :return: 金额
        """
        if order_id not in self.freeze_map:
            raise Exception(f"freeze[{order_id}] ID Not Found")
        rate, amount = self.freeze_map[order_id]
        if amount < real_amount:
            self.available_amount += (amount - real_amount)
            real_amount = amount

        self.freeze_rate -= rate
        self.freeze_amount -= amount

        self.used_rate += rate
        self.used_amount += real_amount

        self.available_amount += (amount - real_amount)
        del self.freeze_map[order_id]
        self.available_amount -= abs(fee)
        self.fee += fee
        self.logger_print("释放金额", (order_id, real_amount, fee))
        return rate

    @locked
    def release_position(self, rate, amount, fee=0):
        """
        释放仓位
        :param fee: 手续费
        :param rate: 冻结比例
        :param amount: 金额
        :return: 金额
        """
        self.available_amount -= abs(fee)
        self.fee += fee
        self.used_amount *= (self.used_rate - rate) / self.used_rate
        self.used_rate -= rate

        self.available_rate += rate
        self.available_amount += amount
        self.logger_print("释放仓位", (rate, amount, fee))

    def get_position(self, symbol) -> Position:
        if symbol in self.quantity_map:
            return self.quantity_map[symbol]

    def get_profit_rate(self, market_data):
        position = self.get_position(market_data.symbol)
        avg_price = position.quantity_amount / position.quantity
        rate = (avg_price - market_data.close) / avg_price
        if position.direction == PositionSide.SHORT:
            rate *= -1
        return rate

    def enough_amount(self):
        """
        判断是否足够余额
        """
        return self.available_rate > PositionManager.MIN_POSITION and self.available_amount > PositionManager.MIN_POSITION * self.total_amount


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
        self.test_mode = strategy_id in ["T0", "V0", "E0"]

    def _data_init(self, market_datas: list):
        pass

    def data_init_params(self, market_data):
        pass

    def post_constructor(self):
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self._wrap_handle)

        def data_init(symbol, market_datas: list):
            self._data_init(market_datas)
            self.__g_map[symbol].data_init_status = 2

        self.bus.subscribe(EventBus.TOPIC_TICK_DATA_INIT, data_init)

        if config.ORDER_ALERT:
            self.bus.subscribe(EventBus.TOPIC_ORDER_DATA, lambda o: notify.alert(o.__str__()))

    def _wrap_handle(self, market_data: G):
        if market_data.symbol not in self.__g_map:
            self.__g_map[market_data.symbol] = G(data_init_status=0)
        self.g = self.__g_map[market_data.symbol]
        self.position = self.position_manager.get_position(symbol=market_data.symbol)

        while not self.test_mode and self.g.data_init_status != 2:
            if self.g.data_init_status == 0:
                params = self.data_init_params(market_data)
                self.g.data_init_status = 1
                if params:
                    self.bus.publish(EventBus.TOPIC_TICK_DATA_INIT_PARAMS, params)
            else:
                time.sleep(0.1)
        self.market_data = market_data

        classes = get_all_base_classes(self.__class__)
        res = []
        for bcls in classes:
            if issubclass(bcls, Filter):
                res.append(bcls.pre(self, market_data, self.position))
        if len(res) == 0 or all(res):
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
        position_signal.position_rate = Decimal("%s" % position_rate)
        position_signal.creator = self.__class__
        position_signal.strategy_id = self.__strategy_id
        position_signal.memo = memo
        position_signal.extend = extend
        self.g.price = self.market_data.close * (1 if side == PositionSide.LONG else -1)
        self.bus.publish(EventBus.TOPIC_STRATEGY_SIGNAL, position_signal)

    def have_position(self):
        return self.position is not None

    def enough_amount(self):
        return self.position_manager.enough_amount()

    def close_position(self, memo="", extend=None):
        """
        平仓指令
        :return: 交易指令
        """
        position_signal = G()
        position_signal.signal_type = "CLOSE"
        position_signal.signal_name = "CLOSE_" + ("LONG" if self.position.direction == PositionSide.LONG else "SHORT")
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
        return self.market_data.close * (1 if self.position.direction == PositionSide.LONG else -1) > self.g.price

    def is_long_position(self):
        return self.position.direction == PositionSide.LONG


@cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
def get_all_strategies_cls_list():
    files = [f for f in os.listdir(Path(__file__).parent)
             if f.endswith(".py") and f not in ["__init__.py", "base.py"]]
    classes = []
    for f in files:
        classes.extend(get_defined_classes(f"leek.strategy.{f[:-3]}"))
    base = BaseStrategy
    if __name__ == "__main__":
        base = get_defined_classes("leek.strategy.base", ["leek.strategy.base.Position"])[0]
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
    print([i for i in get_all_strategies_cls_list()])
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
