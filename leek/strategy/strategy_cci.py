#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/27 21:49
# @Author  : shenglin.li
# @File    : strategy_cci.py
# @Software: PyCharm
"""

"""
from leek.common import logger
from leek.strategy import BaseStrategy
from leek.strategy.base import Position
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import MA, CCI, CCIV2, MACD
from leek.trade.trade import PositionSide


class CCIStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "CCI简单应用"

    def __init__(self, window=20, fast_period=12, slow_period=26, over_sell=-100, over_buy=100):

        self.fast_ma = MA(int(fast_period))
        self.slow_ma = MA(int(slow_period))
        self.cci = CCI(int(window))
        # self.cci = CCIV2(int(window))

        self.over_sell = int(over_sell)
        self.over_buy = int(over_buy)

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 50
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self._calculate(market_data)
        logger.info(f"CCI简单应用数据初始化完成")

    def _calculate(self, data):
        data.fast_ma = self.fast_ma.update(data)
        data.slow_ma = self.slow_ma.update(data)
        last = self.cci.last(1)
        if len(last) > 0:
            data.pre_cci = last[-1]
        data.cci = self.cci.update(data)

    def handle(self):
        k = self.market_data
        self._calculate(k)
        if k.fast_ma is None or k.slow_ma is None or k.cci is None or k.pre_cci is None:
            return
        logger.debug(f"CCI指标 close:{k.close} slow_ma:{k.slow_ma} fast_ma:{k.fast_ma} cci:{k.cci} pre_cci:{k.pre_cci} time eq{self.g.time == k.timestamp}")
        if self.have_position():
            if self.g.time == k.timestamp:
                return
            if self.is_long_position():  # 多
                if k.fast_ma < k.slow_ma or k.cci < 0:
                    self.g.time = k.timestamp
                    self.close_position()
            else:
                if k.fast_ma > k.slow_ma or k.cci > 0:
                    self.g.time = k.timestamp
                    self.close_position()
        else:
            if self.g.time == k.timestamp:
                return
            if k.close > k.fast_ma > k.slow_ma and self.can_long():  # 多
                if k.cci > self.over_buy > k.pre_cci:
                    self.g.time = k.timestamp
                    self.create_order(PositionSide.LONG, self.max_single_position)
            if k.close < k.fast_ma < k.slow_ma and self.can_short():  # 空
                if k.cci < self.over_sell < k.pre_cci:
                    self.g.time = k.timestamp
                    self.create_order(PositionSide.SHORT, self.max_single_position)


class CCIV2Strategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "CCI简单应用2"

    def __init__(self, window=20, fast_period=12, slow_period=26, smoothing_period=9, over_sell=-100, over_buy=100):

        self.macd = MACD(int(fast_period), int(slow_period), int(smoothing_period))
        self.cci = CCI(int(window))
        # self.cci = CCIV2(int(window))

        self.over_sell = int(over_sell)
        self.over_buy = int(over_buy)
        self.ma = MA(3, lambda x: x)

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 50
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self._calculate(market_data)
        logger.info(f"CCI简单应用数据初始化完成")

    def _calculate(self, data):
        data.dif, data.dea = self.macd.update(data)
        last = self.cci.last(1)
        if len(last) > 0:
            data.pre_cci = last[-1]

        data.cci = self.cci.update(data)
        data.cci_ma = self.ma.update(data.cci, finish_v=data.finish == 1)
        # data.cci = self.cci.update(data)
        if data.dif is None or data.dea is None:
            return
        data.m = data.dif - data.dea

    def handle(self):
        k = self.market_data
        self._calculate(k)
        if k.m is None or k.cci is None or k.pre_cci is None:
            return
        logger.debug(f"CCI指标 close:{k.close} dif:{k.dif} dea:{k.dea} m:{k.m} cci:{k.cci} pre_cci:{k.pre_cci} time eq{self.g.time == k.timestamp}")
        if self.have_position():
            if self.g.time == k.timestamp:
                return
            if self.is_long_position():  # 多
                if (k.m < 0 and k.dea < 0) or k.cci < 0:
                    self.g.time = k.timestamp
                    self.close_position()
            else:
                if (k.m > 0 and k.dea > 0) or k.cci > 0:
                    self.g.time = k.timestamp
                    self.close_position()
        else:
            if self.g.time == k.timestamp:
                return
            if (k.m > 0 and k.dea > 0) and self.can_long():  # 多
                if k.cci > self.over_buy > k.pre_cci:
                    self.g.time = k.timestamp
                    self.create_order(PositionSide.LONG, self.max_single_position)
            if (k.m < 0 and k.dea < 0) and self.can_short():  # 空
                if k.cci < self.over_sell < k.pre_cci:
                    self.g.time = k.timestamp
                    self.create_order(PositionSide.SHORT, self.max_single_position)


if __name__ == '__main__':
    pass
