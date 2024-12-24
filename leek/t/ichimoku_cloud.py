#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/18 20:24
# @Author  : shenglin.li
# @File    : dm.py
# @Software: PyCharm
from collections import deque

from leek.t.atr import TR, ATR
from leek.t.ma import EMA, MA
from leek.t.t import T


class IchimokuCloud(T):
    """
    “一目均衡表指标”又称为“ichimoku云图指标”，是由日本著名的技术分析员“Ichimoku Kinko Hyo”（ichi）于1982年提出的。
    D一目均衡表指标由五条线组成；

    tenkan-sen（转换线）：即多空反转信号线。
    转换线算法：过去tenkan_period日最高的最高价加上最低的最低价的和，除以2来计算。
    公式：（tenkan_period日内最高价+tenkan_period日内最低价）/2

    kijun-sen（基线）：即多空趋势变化，可用作追踪止损点。
    基线算法：过去base_period日最高的最高价加上最低的最低价的和，除以2来计算。
    公式：（base_period日内最高价+base_period日内最低价）/2

    senkou span A（跨度A）：即云顶。
    跨度A算法：转换线与基线之和再除以2，然后将结果绘制在前面lagging_shift_period个周期来计算。
    公式：（转换线的值+基线的值）/2

    senkou span B（跨度B）：即云底。
    跨度B算法：最高价与最低价的和除以2，然后将结果绘制在前面lagging_shift_period个周期来计算。
    公式：（leading_span_period日最高价+leading_span_period日最低价）/2

    chikou span（延迟线）：用于显示支撑和压力区域。
    延迟线算法：以当日为第一天算起，第leading_shift_period日的收盘价。
    """

    def __init__(self, tenkan_period=9, base_period=26, leading_span_period=52, lagging_span_period=26, leading_shift_period=26, max_cache=100):
        """
        :param tenkan_period: 转换线周期
        :param base_period: 基准线周期
        :param leading_span_period: 先行带周期
        :param lagging_span_period: 迟行带延迟周期
        :param leading_shift_period: 先行带延迟周期
        :param max_cache: 缓存
        """
        T.__init__(self, max_cache)
        self.tenkan_period = tenkan_period
        self.base_period = base_period
        self.leading_span_period = leading_span_period
        self.lagging_span_period = lagging_span_period  # 迟行带线滞后计算，当前帧无法获取
        self.leading_shift_period = leading_shift_period

        self.q = deque(maxlen=max(tenkan_period, base_period, leading_span_period) + 1)

        self.leading_span_a = deque(maxlen=leading_shift_period)
        self.leading_span_b = deque(maxlen=leading_shift_period)


    def update(self, data):
        # 转换线 基线 云顶 云底
        res = [None, None, None, None]
        try:
            lst = list(self.q)

            # 转换线
            if len(lst) >= self.tenkan_period:
                res[0] = (max(x.high for x in lst[-self.tenkan_period:]) + min(x.low for x in lst[-self.tenkan_period:])) / 2

            # 基准线
            if len(lst) >= self.base_period:
                res[1] =  (max(x.high for x in lst[-self.base_period:]) + min(x.low for x in lst[-self.base_period:])) / 2

            if data.finish == 1:
                # 云顶
                if res[0] is not None and res[1] is not None:
                    self.leading_span_a.append((res[0] + res[1]) / 2)
                # 云底
                if len(lst) >= self.leading_span_period:
                    self.leading_span_b.append((max(x.high for x in lst[-self.leading_span_period:]) + min(x.low for x in lst[-self.leading_span_period:])) / 2)

            if len(self.leading_span_a) >= self.leading_shift_period:
                res[2] = self.leading_span_a[-self.leading_shift_period]
            if len(self.leading_span_b) >= self.leading_shift_period:
                res[3] = self.leading_span_b[-self.leading_shift_period]
            return res
        finally:
            if data.finish == 1:
                self.q.append(data)


if __name__ == '__main__':
    pass
