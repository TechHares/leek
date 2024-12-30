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
    verbose_name = "DMI简单应用"

    def __init__(self):
        self.adx_threshold = 25  # adx 趋势确认
        self.adx_peak_threshold = 70  # adx 极限反转阈值
        self.adx_fallback_threshold = 12  # adx高点回撤

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
            self.g.pre_k = market_data
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
            self.g.pre_adxr = last[0][3]
        adx, up_di, down_di, adxr = self.dmi.update(self.market_data)
        if adx is None or up_di is None or down_di is None:
            return

        # 赋值画图
        kline = self.market_data
        kline.adx, kline.up_di, kline.down_di, kline.adxr = adx, up_di, down_di, adxr
        if self.g.pre_adx is None:
            self.g.pre_adx = adx
            self.g.pre_up_di = up_di
            self.g.pre_down_di = down_di
            self.g.pre_adxr = adxr

    def handle(self):
        self.__calculate()
        k = self.market_data
        pre_k = self.g.pre_k
        if k.finish == 1:
            self.g.pre_k = k

        if pre_k is None or k.adx is None:
            return
        if self.g.high_adx:
            self.g.high_adx = max(self.g.high_adx, k.adx)
        adx_last = [x[0] for x in self.dmi.last(10)]
        if self.market_data.finish != 1:
            adx_last.append(k.adx)
        adx_cross = self.g.pre_adxr < self.adx_threshold < k.adxr < k.adx
        logger.debug(f"DMI,{adx_cross} finish:{self.market_data.finish == 1}, close:{k.close}, adxr:{k.adxr} {self.g.pre_adxr}"
                     f"pdi:{k.up_di} {self.g.pre_up_di}, mdi:{k.down_di} {self.g.pre_down_di}, adx:{k.adx} {self.g.pre_adx}, rsi:{k.rsi_k} {k.rsi_d}")
        if self.have_position():
            # 退出条件
            if self.is_long_position():
                if k.up_di < k.down_di and k.adx > self.adx_threshold and k.adx > self.g.pre_adx: # 趋势反转
                    self.close_position("多头趋势反转平仓")
                    return
                if self.position.avg_price < k.close < pre_k.low:
                    self.close_position("跌破前K低点止损")
                    return
            else:
                if k.up_di > k.down_di and k.adx > self.adx_threshold and k.adx > self.g.pre_adx:  # 趋势反转
                    self.close_position("空头趋势反转平仓")
                    return

                if self.position.avg_price > k.close > pre_k.high:
                    self.close_position("涨破前K高点止损")
                    return
            # adx 极限退出
            if self.adx_peak_threshold < k.adx < self.g.pre_adx:
                self.close_position("adx极限阈值止盈")
                return
            if k.adx < k.adxr < self.g.pre_adxr and  k.adx < self.g.pre_adx:
                self.close_position("adxr回落交叉")
                return
        elif adx_cross:  # 无仓位 考虑开仓
            self.g.high_adx = k.adx
            logger.debug(f"CROSS, 多头条件:{k.up_di > k.down_di} and {k.down_di <= self.g.pre_down_di}, "
                         f"空头条件:{k.up_di < k.down_di} and {k.up_di <= self.g.pre_up_di}")
            if k.up_di > k.down_di and k.down_di <= self.g.pre_down_di: # 多头
                logger.info(f"DMI多头开仓, 趋势成立, adx:{k.adx}, up_di:{k.up_di}, down_di:{k.down_di}")
                self.create_order(PositionSide.LONG, self.max_single_position)

            if k.up_di < k.down_di and k.up_di <= self.g.pre_up_di :  # 空头
                logger.info(f"DMI空头开仓, 趋势成立, adx:{k.adx}, up_di:{k.up_di}, down_di:{k.down_di}")
                self.create_order(PositionSide.SHORT, self.max_single_position)


if __name__ == '__main__':
    pass
