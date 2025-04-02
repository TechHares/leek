#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/10 19:45
# @Author  : shenglin.li
# @File    : sar.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.common import G
from leek.t import MA, EMA
from leek.t.t import T


class MACD(T):

    def __init__(self, fast_period=12, slow_period=26, moving_period=9, ma=MA, max_cache=10):
        T.__init__(self, max_cache=max_cache)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.moving_period = moving_period

        self.fast_ma = ma(self.fast_period)
        self.slow_ma = ma(self.slow_period)
        self.dea = ma(self.moving_period)

    def update(self, data):
        fast = self.fast_ma.update(data)
        slow = self.slow_ma.update(data)
        if slow is None or fast is None:
            return None, None
        dif = fast - slow
        g = G(close=dif, finish=data.finish)
        dea = self.dea.update(g)
        if dea is None:
            return dif, None
        if data.finish == 1:
            self.cache.append((dif, dea))
        return dif, dea


class Divergence:
    def __init__(self, divergence_threshold=1, allow_cross_zero=True, close_price_divergence=True,
                 peak_price_divergence=True, peak_price_divergence_advance=True,
                 m_area_divergence=True, dea_pull_back=True, pull_back_rate=0, divergence_rate=0.9):
        """
        初始化参数
        :param allow_cross_zero:               允许前次势峰 穿过0轴
        :param divergence_threshold:           背离参数阈值   close\极值*area/dif 背离的数量
        :param close_price_divergence:         收盘价背离    启用收盘价背离判断
        :param peak_price_divergence:          峰值背离      启用极值价背离
        :param peak_price_divergence_advance:  峰值背离增强  开启后极值背离还会考虑K线的形态
        :param m_area_divergence:              能量柱背离    启用能量柱面积背离
        :param pull_back_rate:                 拉回率       背离双峰之间回拉0轴比例
        :param dea_pull_back:                  DEA线拉回    启用DEA线拉回判断 不启用会使用DIF线
        :param divergence_rate:                背离率       后一次背离前一次的比值
        """
        self.divergence_threshold = divergence_threshold
        self.allow_cross_zero = allow_cross_zero
        self.close_price_divergence = close_price_divergence
        self.peak_price_divergence = peak_price_divergence
        self.peak_price_divergence_advance = peak_price_divergence_advance
        self.m_area_divergence = m_area_divergence
        self.dea_pull_back = dea_pull_back
        self.pull_back_rate = pull_back_rate
        self.divergence_rate = divergence_rate

    def is_top_divergence(self, data) -> bool:
        """
        顶背离
        :param data:
        :return:
        """
        if len(data) < 10:
            return False
        top_k = max(data[-4:], key=lambda x: x.high)
        if not data[-1].m < data[-2].m < data[-3].m > data[-4].m: #  保证最近三次能量柱下降
            return False
        if not min(data[-1].dif, data[-2].dif, data[-3].dif) > 0:  #  保证黄线在水上>0
            return False
        data, params = self._top_divergence_iter(data)
        # 当次上升过程参数
        min_pull_back = Decimal('Infinity')
        params2 = None
        while len(data) > 3:
            data, bottom_params = self._bottom_divergence_iter(data)
            min_pull_back = min(min_pull_back, bottom_params[4] if self.dea_pull_back else bottom_params[3])

            # 前一次上升过程参数
            data, params2 = self._top_divergence_iter(data)
            if params2[0] >= 3:
                max_line = params2[4] if self.dea_pull_back else params2[3]
                if min_pull_back < 0 and abs(min_pull_back * 3) > max_line: # 拉回水下太多，趋势已经破坏掉了
                    return False
                # 回拉判断
                if max_line == 0 or (max_line - min_pull_back) / max_line < self.pull_back_rate:  # 回拉比例不足
                    return False
                break

        if params2 is None or params2[0] < 3:
            return False
        if not self.allow_cross_zero and params2[7].dif < 0:
            return False

        divergence_count = 0
        line_divergence = abs(params[3] / params2[3])  < self.divergence_rate  # 黄线是否低了
        m_divergence = self.m_area_divergence and params[6] < params2[6] and params[5] < params2[5]    # 能量柱是否低了
        if m_divergence and self.peak_price_divergence_advance:  # 顶上K是否有很长的上影线
            m_divergence = top_k.close < top_k.open or (top_k.high - top_k.close) > (top_k.close - top_k.open)

        close_new_high = self.close_price_divergence and params[1] > params2[1] # 收盘价是否新高
        peak_new_high = self.peak_price_divergence and params[2] > params2[2]   # 极值价是否新高
        if close_new_high:
            if line_divergence:
                divergence_count += 1
            if m_divergence:
                divergence_count += 1
        if peak_new_high:
            if line_divergence:
                divergence_count += 1
            if m_divergence:
                divergence_count += 1

        return divergence_count >= self.divergence_threshold


    def is_bottom_divergence(self, data) -> bool:
        """
        底背离
        :param data:
        :return:
        """
        if len(data) < 10:
            return False
        bottom_k = min(data[-4:], key=lambda x: x.low)
        if not data[-1].m > data[-2].m > data[-3].m < data[-4].m:  #  保证最近三次能量柱上升
            return False
        if not max(data[-1].dif, data[-2].dif, data[-3].dif) < 0:  #  保证黄线在水下<0
            return False
        data, params = self._bottom_divergence_iter(data)
        # 当次下降过程参数
        max_pull_back = Decimal('-Infinity')
        params2 = None
        while len(data) > 3:
            data, top_params = self._top_divergence_iter(data)
            max_pull_back = max(max_pull_back, top_params[4] if self.dea_pull_back else top_params[3])
            # 前一次下降过程参数
            data, params2 = self._bottom_divergence_iter(data)
            if params2[0] >= 3:
                min_line = params2[4] if self.dea_pull_back else params2[3]
                if max_pull_back > 0 and max_pull_back * 3 > abs(max_pull_back):  # 拉上水太多，趋势已经破坏掉了
                    return False
                # 回拉判断
                if min_line == 0 or (max_pull_back - min_line) / abs(min_line) < self.pull_back_rate:  # 回拉比例不足
                    return False
                break

        if params2 is None or params2[0] < 3:
            return False
        if not self.allow_cross_zero and params2[7].dif > 0:
            return False

        divergence_count = 0

        line_divergence = abs(params[3] / params2[3]) < self.divergence_rate  # 黄线是否高了
        m_divergence = self.m_area_divergence and params[6] < params2[6] and params[5] > params2[5]   # 能量柱是否高了
        if m_divergence and self.peak_price_divergence_advance:  # 顶上K是否有很长的上影线
            m_divergence = bottom_k.close > bottom_k.open or (bottom_k.open - bottom_k.close) < (bottom_k.close - bottom_k.low)
        close_new_low = self.close_price_divergence and params[1] < params2[1] # 收盘价是否新低
        peak_new_low = self.peak_price_divergence and params[2] < params2[2]   # 极值价是否新低
        if close_new_low:
            if line_divergence:
                divergence_count += 1
            if m_divergence:
                divergence_count += 1
        if peak_new_low:
            if line_divergence:
                divergence_count += 1
            if m_divergence:
                divergence_count += 1
        return divergence_count >= self.divergence_threshold

    def _top_divergence_iter(self, data, area_all=False):
        idx = 1
        # K线数量, 最高收盘价, 最高高价, 最大dif值, 最大dea值, 最大能量柱, 能量柱面积
        params = [0, Decimal('-Infinity'), Decimal('-Infinity'), Decimal('-Infinity'), Decimal('-Infinity'), Decimal('-Infinity'), 0, None]
        while idx < len(data):
            k = data[-idx]
            if k.m < 0:
                break
            idx += 1
            params[0] += 1
            params[1] = max(params[1], k.close)
            params[2] = max(params[2], k.high)
            params[3] = max(params[3], k.dif)
            params[4] = max(params[4], k.dea)
            params[5] = max(params[5], k.m)
            params[7] = k
        if area_all:
            params[6] = sum(k.m for k in data[-idx+1:])
        else:
            params[6] = sum(k.m for k in data[-idx+1:-1]) * 2
        return data[:-idx+1], params

    def _bottom_divergence_iter(self, data, area_all=False):
        idx = 1
        # K线数量, 最低收盘价, 最低低价, 最小dif值, 最小dea值, 最小能量柱, 能量柱面积
        params = [0, Decimal('Infinity'), Decimal('Infinity'), Decimal('Infinity'), Decimal('Infinity'), Decimal('Infinity'), 0, None]
        while idx < len(data):
            k = data[-idx]
            if k.m > 0:
                break
            idx += 1
            params[0] += 1
            params[1] = min(params[1], k.close)
            params[2] = min(params[2], k.low)
            params[3] = min(params[3], k.dif)
            params[4] = min(params[4], k.dea)
            params[5] = min(params[5], k.m)
            params[7] = k
        if area_all:
            params[6] = -sum(k.m for k in data[-idx+1:])
        else:
            params[6] = (-sum(k.m for k in data[-idx+1:-1])) * 2
        return data[:-idx+1], params


if __name__ == '__main__':
    pass

