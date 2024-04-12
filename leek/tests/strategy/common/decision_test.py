#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/9 20:21
# @Author  : shenglin.li
# @File    : decision.py
# @Software: PyCharm
import unittest
from decimal import Decimal
from collections import namedtuple

from leek.runner.view import ViewWorkflow
from leek.strategy.common.decision import OBVDecisionNode, MADecisionNode, MACDDecisionNode, RSIDecisionNode, \
    VolumeDecisionNode, BollDecisionNode, StochasticDecisionNode, PSYDecisionNode, PVTDecisionNode, SMIIODecisionNode, \
    STDecisionNode, MomDecisionNode


class TestDecisionNode(unittest.TestCase):
    def setUp(self):
        workflow = ViewWorkflow(None, "5m", 1710000000000, 1710604800000, "ZRXUSDT")
        self.data = workflow.get_data_g()

    def test_OBVDecisionNode(self):
        node = OBVDecisionNode(fast_period=5, slow_period=10)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_MADecisionNode(self):
        node = MADecisionNode(fast_period=20, slow_period=30)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_MACDDecisionNode(self):
        node = MACDDecisionNode(fast_period=5, slow_period=17, moving_period=7)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_RSIDecisionNode(self):
        node = RSIDecisionNode(period=14, over_buy=70, over_sell=30)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_VolumeDecisionNode(self):
        node = VolumeDecisionNode(fast_period=20, slow_period=30)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_BollDecisionNode(self):
        node = BollDecisionNode(period=20, num_std_devs=5)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_StochasticDecisionNode(self):
        node = StochasticDecisionNode(period=14, moving_period=3, over_buy=70, over_sell=30)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_PSYDecisionNode(self):
        node = PSYDecisionNode(period=60, over_buy=75, over_sell=25)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_PVTDecisionNode(self):
        node = PVTDecisionNode(fast_period=5, slow_period=10)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_SMIIODecisionNode(self):
        node = SMIIODecisionNode(fast_period=5, slow_period=20, sigma_period=5)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_STDecisionNode(self):
        node = STDecisionNode(period=10, factory=3)
        evaluation = node.evaluation(self.data)
        print(evaluation)

    def test_MomDecisionNode(self):
        node = MomDecisionNode(period=10, price_type=1)
        evaluation = node.evaluation(self.data)
        print(evaluation)


if __name__ == '__main__':
    unittest.main()
