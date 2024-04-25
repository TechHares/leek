#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 22:24
# @Author  : shenglin.li
# @File    : trade_backtest.py
# @Software: PyCharm
import random
from decimal import Decimal

from leek.common import EventBus, get_logger, G
from leek.common.utils import decimal_quantize
from leek.trade.trade import Trader, Order, OrderType, PositionSide


class BacktestTrader(Trader):
    verbose_name = "回测交易"
    def __init__(self, slippage: Decimal = 0.0, fee_type: int = 0, fee: Decimal = 0,
                 limit_order_execution_rate: int = 100, volume_limit: int = 4):
        """
        :param slippage: 滑点幅度，0.0 - 1.0 成交价会在该幅度内随机产生 [(1-slippage)*报价, (1+slippage)*报价] 仅针对市价单有效
        :param fee_type: 费用收取方式类型，0 无费用，1 固定费用，2 成交额固定比例，3 单位成交固定费用
        :param fee: 费率， 费用收取方式类型 0 时无效， 1 时表示固定费用， 2 时表示固定比例
        :param limit_order_execution_rate: 限价单成交率， 1 - 100, 仅针对限价单有效, 成交额=报单额*random(limit_order_execution_rate% ~ 1)
        :param volume_limit: 成交量小数保留位数
        """
        self.slippage = Decimal(slippage)
        if self.slippage > 1:
            self.slippage = Decimal(1)
        if self.slippage < 0:
            self.slippage = Decimal(0)

        self.fee_type = int(fee_type)
        if self.fee_type not in [0, 1, 2, 3]:
            self.fee_type = 0
        self.fee = Decimal(fee)

        self.limit_order_execution_rate = Decimal(limit_order_execution_rate)
        if self.limit_order_execution_rate < 1:
            self.limit_order_execution_rate = 1
        if self.limit_order_execution_rate > 100:
            self.limit_order_execution_rate = 100

        self.volume_limit = int(volume_limit)

    def order(self, order: Order):
        price_n = abs(order.price.as_tuple().exponent) if order.price is not None else 6
        amount_n = abs(order.amount.as_tuple().exponent)

        #  1. 计算成交价
        order.transaction_price = order.price
        if order.type == OrderType.MarketOrder and self.slippage > 0:  # 市价单
            slippage = Decimal(random.random()) * (2 * self.slippage) + (1 - self.slippage)
            order.transaction_price = decimal_quantize(order.price * slippage, price_n)

        #  2. 计算成交量
        order.sz = order.sz if order.sz else decimal_quantize(order.amount / order.transaction_price, self.volume_limit)
        order.cct = 1
        order.transaction_volume = order.sz
        if order.type == OrderType.LimitOrder:  # 限价单
            random_num = random.randint(self.limit_order_execution_rate, 100)  # 成交量波动
            sz_n = abs(order.sz.as_tuple().exponent)
            order.transaction_volume = decimal_quantize(order.sz * random_num / 100, sz_n)

        #  3. 计算成交额
        order.transaction_amount = decimal_quantize(order.transaction_volume * order.transaction_price, amount_n)

        #  4. 计算手续费
        if self.fee_type == 0:
            order.fee = Decimal(0)
        elif self.fee_type == 1:
            order.fee = self.fee
        elif self.fee_type == 2:
            order.fee = order.transaction_amount * self.fee
        elif self.fee_type == 3:
            order.fee = order.transaction_volume * self.fee
        pos_trade = G()
        pos_trade.order_id = order.order_id
        pos_trade.transaction_price = order.price
        pos_trade.lever = 1
        pos_trade.fee = abs(order.fee)
        pos_trade.pnl = 0
        pos_trade.sz = order.transaction_volume
        pos_trade.cancel_source = ""
        pos_trade.symbol = order.symbol

        pos_trade.ct_val = 1
        pos_trade.transaction_volume = pos_trade.sz * pos_trade.ct_val
        amt = decimal_quantize(pos_trade.transaction_volume * pos_trade.transaction_price, 8)
        pos_trade.transaction_amount = abs(Decimal(amt))
        pos_trade.side = order.side
        self._trade_callback(pos_trade)


if __name__ == '__main__':
    trader = BacktestTrader()
    Trader.__init__(trader, EventBus(), get_logger("d"))
    print(trader.order(Order("1", "1", OrderType.MarketOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"),
                             PositionSide.LONG)))
