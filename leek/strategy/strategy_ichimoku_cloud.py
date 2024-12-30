#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/20 20:42
# @Author  : shenglin.li
# @File    : strategy_ichmoku_cloud.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import numpy as np

from leek.common import logger
from leek.strategy import BaseStrategy
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData, FallbackTakeProfit
from leek.t import LLT, FRAMA, MA, IchimokuCloud, StochRSI
from leek.trade.trade import PositionSide
from scipy.signal import hilbert


class IchimokuCloudStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "一目云图简单应用"

    def __init__(self):
        self.ichimoku_cloud = IchimokuCloud()

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 100
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.__calculate(market_data)
        logger.info(f"一目云图初始化完成")

    def __calculate(self, market_data):
        # 转换线 基线 云顶 云底
        tenkan_line, base_line, span_a, span_b = self.ichimoku_cloud.update(market_data)
        if tenkan_line is None or base_line is None or span_a is None or span_b is None :
            return
        market_data.tenkan_line = tenkan_line
        market_data.base_line = base_line
        market_data.span_a = span_a
        market_data.span_b = span_b
        lagging_k, lagging_cloud = self.ichimoku_cloud.get_lagging_data()
        if lagging_cloud is None:
            return
        self.g.lagging_k = lagging_k
        self.g.lagging_tenkan_line = lagging_cloud[0]
        self.g.lagging_base_line = lagging_cloud[1]
        self.g.lagging_span_a = lagging_cloud[2]
        self.g.lagging_span_b = lagging_cloud[3]
        logger.debug(f"tenkan_line={tenkan_line}, base_line={base_line}, span_a={span_a}, span_b={span_b}, price={market_data.close}"
                     f", lagging_tenkan_line={lagging_cloud[0]}, lagging_base_line={lagging_cloud[1]},"
                     f" lagging_span_a={lagging_cloud[2]}, lagging_span_b={lagging_cloud[3]}, lagging={lagging_k.close}")


    def handle(self):
        """
        买入信号：
        1. K线在云上方
        2. k线在基准线上方
        3. 转换线在基准线上方
        4. 迟行线在K线上方
        5. 迟行线上传 基准线 转换线 云图
        卖出信号：
        1. 转换线跌破基准线
        2. K线跌破云层
        3. 迟行线下穿K线
        """
        k = self.market_data
        self.__calculate(k)
        if self.g.lagging_k is None:
            return
        if self.have_position():
            if self.is_long_position(): # 多头仓位
                if k.tenkan_line < k.base_line and k.low < max(k.span_a, k.span_b) and k.close < self.g.lagging_k.high: # 多头 转换线 基准线 云层 均在K线下方:
                    self.close_position("出局")
            else:
                if k.tenkan_line > k.base_line and k.high > min(k.span_a, k.span_b) and k.close > self.g.lagging_k.low: # 空头 转换线 基准线 云层 均在K线上方:
                    self.close_position("出局")
        else:
            if self.can_long(): # 做多
                if (k.low > k.span_a > k.span_b and k.low > k.tenkan_line > k.base_line and # K线在云上方 k线在基准线上方 转换线在基准线上方
                        k.close > self.g.lagging_k.high and self.g.pre_lagging_long and k.close > max(self.g.lagging_tenkan_line, self.g.lagging_base_line, self.g.lagging_span_a, self.g.lagging_span_b)): # 迟行线在K线上方 迟行线上传 基准线 转换线 云图
                    self.create_order(PositionSide.LONG, self.max_single_position)
            if self.can_short(): # 做空
                if (k.high < k.span_a < k.span_b and k.high < k.tenkan_line < k.base_line and # K线在云下方 k线在基准线下方 转换线在基准线下方
                        k.close < self.g.lagging_k.low and self.g.pre_lagging_short and k.close < min(self.g.lagging_tenkan_line, self.g.lagging_base_line, self.g.lagging_span_a, self.g.lagging_span_b)): # 迟行线下穿K线
                    self.create_order(PositionSide.SHORT, self.max_single_position)
        if k.finish == 1:
            self.g.pre_lagging_long = k.span_a < k.span_b
            self.g.pre_lagging_short = k.span_a > k.span_b


if __name__ == '__main__':
    pass
