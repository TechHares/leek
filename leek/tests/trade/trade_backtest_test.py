#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 10:53
# @Author  : shenglin.li
# @File    : trade_backtest_test.py
# @Software: PyCharm
import unittest
from decimal import Decimal

from leek.trade.trade import Order, OrderType, PositionSide
from leek.trade.trade_backtest import BacktestTrader


class TestDemoClass(unittest.TestCase):
    def setUp(self):
        pass

    def test_order_market_order_with_slippage(self):
        trader = BacktestTrader(Decimal("0.005"), 0, Decimal(20), 90, 4)

        order = Order("1", "1", OrderType.MarketOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"), PositionSide.LONG)
        result = trader.order(order)
        self.assertNotEqual(result.transaction_price, Decimal("20.369"))
        self.assertEqual(result.transaction_volume, result.sz)
        self.assertEqual(result.fee, Decimal(0))

        order = Order("1", "1", OrderType.LimitOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"), PositionSide.LONG)
        result = trader.order(order)
        self.assertEqual(result.transaction_price, Decimal("20.369"))
        self.assertNotEqual(result.transaction_volume, result.sz)
        self.assertEqual(result.fee, Decimal(0))

    def test_order_with_fee_type_1(self):
        trader = BacktestTrader(Decimal("0.005"), 1, Decimal(20), 90, 4)

        order = Order("1", "1", OrderType.MarketOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"), PositionSide.LONG)
        result = trader.order(order)

        self.assertEqual(result.fee, Decimal(20))

    def test_order_with_fee_type_2(self):
        trader = BacktestTrader(Decimal("0.005"), 2, Decimal("0.01"), 90, 4)

        order = Order("1", "1", OrderType.MarketOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"), PositionSide.LONG)
        result = trader.order(order)

        self.assertEqual(result.fee, Decimal("0.01") * result.transaction_amount)

    def test_order_with_fee_type_3(self):
        trader = BacktestTrader(Decimal("0.005"), 3, Decimal("0.01"), 90, 4)

        order = Order("1", "1", OrderType.MarketOrder, "BTCUSDT", Decimal("100"), Decimal("20.369"), PositionSide.LONG)
        result = trader.order(order)

        self.assertEqual(result.fee, Decimal("0.01") * result.transaction_volume)


if __name__ == '__main__':
    unittest.main()
