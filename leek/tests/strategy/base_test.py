#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/12 01:46
# @Author  : shenglin.li
# @File    : base_test.py
# @Software: PyCharm
import time
import unittest
from decimal import Decimal

from leek.common import EventBus, G
from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.trade import SwapOkxTrader
from leek.trade.trade import PositionSide, Trader
from leek.trade.trade_backtest import BacktestTrader


class LongStrategy(BaseStrategy):
    def __init__(self, bus):
        BaseStrategy.__init__(self, 1, bus, 1000)

    def handle(self):
        if self.have_position():
            self.close_position()
        else:
            self.create_order(PositionSide.LONG)


class ShortStrategy(BaseStrategy):
    def __init__(self, bus):
        BaseStrategy.__init__(self, 1, bus, 1000)

    def handle(self):
        if self.have_position():
            self.close_position()
        else:
            self.create_order(PositionSide.SHORT)

class TestBase(unittest.TestCase):

    def test_short(self):
        bus = EventBus()
        self.trader = BacktestTrader(fee_type=2, fee=Decimal("0.02"))
        Trader.__init__(self.trader, bus)
        data = [
            G(symbol="test", close=Decimal("100"), timestamp=1),
            G(symbol="test", close=Decimal("50"), timestamp=2)
        ]
        strategy = ShortStrategy(bus)

        for d in data:
            print(d.__json__())
            bus.publish(EventBus.TOPIC_TICK_DATA, d)
        assert strategy.position_manager.available_amount == Decimal("1235")

    def test_long(self):
        bus = EventBus()
        self.trader = BacktestTrader(fee_type=2, fee=Decimal("0.01"))
        Trader.__init__(self.trader, bus)
        strategy = LongStrategy(bus)
        data = [
            G(symbol="test", close=Decimal("50"), timestamp=2),
            G(symbol="test", close=Decimal("100"), timestamp=1),
        ]

        for d in data:
            bus.publish(EventBus.TOPIC_TICK_DATA, d)
        print(strategy.position_manager.available_amount)
        assert strategy.position_manager.available_amount == Decimal("1485")

    def test_short1(self):
        bus = EventBus()
        self.trader = BacktestTrader()
        Trader.__init__(self.trader, bus)
        data = [
            G(symbol="test", close=Decimal("100"), timestamp=1),
            G(symbol="test", close=Decimal("50"), timestamp=2)
        ]
        strategy = ShortStrategy(bus)

        for d in data:
            print(d.__json__())
            bus.publish(EventBus.TOPIC_TICK_DATA, d)
        assert strategy.position_manager.available_amount == Decimal("1250")

    def test_long2(self):
        bus = EventBus()
        self.trader = BacktestTrader()
        Trader.__init__(self.trader, bus)
        strategy = LongStrategy(bus)
        data = [
            G(symbol="test", close=Decimal("50"), timestamp=2),
            G(symbol="test", close=Decimal("100"), timestamp=1),
        ]

        for d in data:
            bus.publish(EventBus.TOPIC_TICK_DATA, d)
        print(strategy.position_manager.available_amount)
        assert strategy.position_manager.available_amount == Decimal("1500")


if __name__ == '__main__':
    unittest.main()
