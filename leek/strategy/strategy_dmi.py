#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/19 20:42
# @Author  : shenglin.li
# @File    : strategy_dmi.py
# @Software: PyCharm
from decimal import Decimal

from leek.common import logger
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import DMI, StochRSI
from leek.trade.trade import PositionSide


class DMIStrategy(DynamicRiskControl, JustFinishKData, PositionRateManager, BaseStrategy):
    verbose_name = "DMI择时例子"

    def __init__(self):
        self.adx_threshold = 25  # adx 趋势确认
        self.adx_peak_threshold = 50  # adx 极限反转阈值
        self.adx_fallback_threshold = 12  # adx高点回撤

        # RSI超卖超买阈值
        self.over_buy_threshold = 75
        self.over_sell_threshold = 25
        self.peak_over_buy_threshold = 92
        self.peak_over_sell_threshold = 8

        self.dmi = DMI()
        self.symbol = None

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 50
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.dmi.update(market_data)
        logger.info(f"DMI数据初始化完成")

    def __calculate(self):
        if self.symbol is None:
            self.symbol = self.market_data.symbol
        assert self.symbol==self.market_data.symbol, "不支持多个标的"
        last = self.dmi.last(1)
        if len(last) > 0:
            self.g.pre_adx = last[0][0]
            self.g.pre_up_di = last[0][1]
            self.g.pre_down_di = last[0][2]
        adx, up_di, down_di = self.dmi.update(self.market_data)
        if adx is None or up_di is None or down_di is None:
            return

        # 赋值画图
        kline = self.market_data
        kline.adx, kline.up_di, kline.down_di = adx, up_di, down_di
        if self.g.pre_adx is None:
            self.g.pre_adx = adx
            self.g.pre_up_di = up_di
            self.g.pre_down_di = down_di

    def handle(self):
        self.__calculate()
        k = self.market_data
        if k.adx is None:
            return
        if self.g.high_adx:
            self.g.high_adx = max(self.g.high_adx, k.adx)
        adx_last = [x[0] for x in self.dmi.last(10)]
        if self.market_data.finish != 1:
            adx_last.append(k.adx)
        adx_cross = self.g.pre_adx < self.adx_threshold < k.adx
        logger.debug(f"DMI,{adx_cross} finish:{self.market_data.finish == 1}, close:{k.close}, stop_loss_price:{self.g.stop_loss_price}"
                    f"pdi:{k.up_di} {self.g.pre_up_di}, mdi:{k.down_di} {self.g.pre_down_di}, adx:{k.adx} {self.g.pre_adx}")
        if self.have_position():
            # 退出条件
            if self.is_long_position():
                if k.up_di < k.down_di and k.adx > self.adx_threshold and k.adx > self.g.pre_adx: # 趋势反转
                    self.close_position("多头趋势反转平仓")
                    return
            else:
                if k.up_di > k.down_di and k.adx > self.adx_threshold and k.adx > self.g.pre_adx:  # 趋势反转
                    self.close_position("空头趋势反转平仓")
                    return
            if self.g.high_adx - k.adx > self.adx_fallback_threshold:
                self.close_position("adx下降过多")
            # adx 极限退出
            if self.adx_peak_threshold < k.adx < self.g.pre_adx:
                self.close_position("adx极限阈值止盈")
                return
        elif adx_cross:  # 无仓位 考虑开仓
            self.g.high_adx = k.adx
            logger.info(f"CROSS, 多头条件:{k.up_di > k.down_di} and {k.down_di <= self.g.pre_down_di}, "
                        f"空头条件:{k.up_di < k.down_di} and {k.up_di <= self.g.pre_up_di}")
            if k.up_di > k.down_di and k.down_di <= self.g.pre_down_di: # 多头
                logger.info(f"DMI多头开仓, 趋势成立, adx:{k.adx}, up_di:{k.up_di}, down_di:{k.down_di}")
                self.create_order(PositionSide.LONG, self.max_single_position)

            if k.up_di < k.down_di and k.up_di <= self.g.pre_up_di:  # 空头
                logger.info(f"DMI空头开仓, 趋势成立, adx:{k.adx}, up_di:{k.up_di}, down_di:{k.down_di}")
                self.create_order(PositionSide.SHORT, self.max_single_position)


if __name__ == '__main__':
    pass
