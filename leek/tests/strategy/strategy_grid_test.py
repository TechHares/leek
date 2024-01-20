#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:47
# @Author  : shenglin.li
# @File    : strategy_grid.py
# @Software: PyCharm


from leek.strategy.strategy import BaseStrategy
from leek.strategy.strategy_grid import SingleGridStrategy
from leek.trade.trade import Order, PositionSide as PS, OrderType as OT

import unittest
from mock import MagicMock

class TestDemoClass(unittest.TestCase):
    def setUp(self):
        self.demo_class = SingleGridStrategy(1, "BTC", 100, 200, 100000000, 0.1, 10, 1, PS.LONG)
        self.market_data = {"close_price": 100}

    def test_handle_should_return_position_order_if_price_is_outside_risk_rate(self):
        self.market_data["close_price"] = 200
        self.demo_class.max_price = 150
        self.demo_class.risk_rate = 0.1
        result = self.demo_class.handle(self.market_data)
        self.assertIsNone(result)

    def test_handle_should_return_none_if_price_is_outside_max_min_price(self):
        self.market_data["close_price"] = 200
        result = self.demo_class.handle(self.market_data)
        self.assertIsNone(result)

    def test_handle_should_return_order_with_long_side_if_price_is_within_max_min_price_and_long_direction(self):
        self.market_data["close_price"] = 120
        self.demo_class.max_price = 150
        self.demo_class.min_price = 100
        self.demo_class.direction = PS.LONG
        result = self.demo_class.handle(self.market_data)
        self.assertIsInstance(result, Order)
        self.assertEqual(result.order_id, "")
        self.assertEqual(result.type, OT.MarketOrder)
        self.assertEqual(result.symbol, self.demo_class.symbol)
        self.assertEqual(result.side, PS.LONG)

    def test_handle_should_return_order_with_short_side_if_price_is_within_max_min_price_and_short_direction(self):
        self.market_data["close_price"] = 120
        self.demo_class.max_price = 150
        self.demo_class.min_price = 100
        self.demo_class.direction = PS.SHORT
        result = self.demo_class.handle(self.market_data)
        self.assertIsInstance(result, Order)
        self.assertEqual(result.order_id, "")
        self.assertEqual(result.type, OT.MarketOrder)
        self.assertEqual(result.symbol, self.demo_class.symbol)
        self.assertEqual(result.side, PS.SHORT)

    def test_handle_should_update_current_grid_to_dt_gird(self):
        self.market_data["close_price"] = 120
        self.demo_class.max_price = 150
        self.demo_class.min_price = 100
        self.demo_class.direction = PS.LONG
        self.demo_class.current_grid = 2
        self.demo_class.grid_price = 10
        if self.demo_class.direction == PS.LONG:
            dt_price = 30
        else:
            dt_price = 20

        dt_gird = dt_price / 10
        result = self.demo_class.handle(self.market_data)
        self.assertEqual(self.demo_class.current_grid, dt_gird)

    def test_handle_should_return_none_if_dt_gird_is_equal_to_current_grid(self):
        self.market_data["close_price"] = 120
        self.demo_class.max_price = 150
        self.demo_class.min_price = 100
        self.demo_class.direction = PS.SHORT
        self.demo_class.current_grid = 2
        self.demo_class.grid_price = 10
        result = self.demo_class.handle(self.market_data)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
