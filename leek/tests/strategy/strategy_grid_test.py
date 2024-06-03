#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 21:27
# @Author  : shenglin.li
# @File    : strategy_boll_choose_test.py
# @Software: PyCharm
import datetime
import time
import unittest
from decimal import Decimal

import pandas as pd
from plotly.subplots import make_subplots

from leek.common.utils import DateTime
from leek.runner.symbol_choose import SymbolChooseWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy import BaseStrategy
from leek.strategy.common import SymbolFilter, PositionSideManager
from leek.strategy.strategy_bollinger_bands import BollingerBandsV2Strategy
from leek.strategy.strategy_grid import SingleGridStrategy
from leek.tests.strategy.symbol_choose_test import draw_fig
from leek.trade.trade import PositionSide


class TestGridStrategy(unittest.TestCase):
    def test_grid(self):
        self.strategy = SingleGridStrategy(min_price="1.2", max_price="1.4", risk_rate=0.1, grid=10)

        SymbolFilter.__init__(self.strategy, "TNSR-USDT-SWAP")
        PositionSideManager.__init__(self.strategy, PositionSide.SHORT)
        workflow = ViewWorkflow(self.strategy, "1m", "2024-06-03 19:00", "2024-06-03 21:44", "TNSR-USDT-SWAP")
        workflow.start()
        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        print(len(df))
        fig.show()

    def test_(self):
        sz = Decimal("64")
        sz *= Decimal("0.1") / Decimal("0.9")
        print(sz)


if __name__ == '__main__':
    unittest.main()
