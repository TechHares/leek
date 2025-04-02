#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/29 20:17
# @Author  : shenglin.li
# @File    : strategy_chan1.py
# @Software: PyCharm

"""
120 均线  macd 订方向

"""
from decimal import Decimal

from leek.common import logger
from leek.common.utils import DateTime
from leek.strategy import BaseStrategy
from leek.strategy.common import StopLoss
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import JustFinishKData
from leek.t import ChanBIManager, BiFXValidMethod, ChanSegmentManager, ChanZSManager, Chan, MACD, MA, MA_TYPE
from leek.trade.trade import PositionSide


class ChanV2Strategy(StopLoss, PositionRateManager, JustFinishKData, BaseStrategy):
    verbose_name = "缠论V2(区间套)"

    def __init__(self, exclude_equal=False, zs_max_level=2, allow_similar_zs=False,
                 fast_period=12, slow_period=26, smoothing_period=9, mean_type="MA", divergence_rate=0.9):
        self.init_k_num = 2000  # 初始化拉取k线数量
        self.allow_similar_zs = allow_similar_zs
        self.exclude_equal = exclude_equal
        self.zs_max_level = zs_max_level
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.smoothing_period = smoothing_period
        self.mean_type = mean_type
        self.divergence_rate = divergence_rate
        self.chan = Chan(exclude_equal=exclude_equal, zs_max_level=zs_max_level, allow_similar_zs=allow_similar_zs)
        ma_func = MA_TYPE[mean_type.upper()]

        self.macd = MACD(int(fast_period), int(slow_period), int(smoothing_period), ma_func)
        self.divergence_rate = float(divergence_rate)
        self.max_delay_k_num = 5  # 最大允许延迟K线数量

        self.current_dr = None
        self.current_dr_count = None


    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": self.init_k_num
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self._calculate(market_data)
        logger.info(f"缠论初始化完成")

    def _calculate(self, k):
        self.chan.update(k)
        dif, dea = self.macd.update(k)
        if dif is not None and dea is not None:
            k.dif = dif
            k.dea = dea
            k.m = dif - dea
        else:
            k.dif = 0
            k.dea = 0
            k.m = 0

    def handle(self):
        self._calculate(self.market_data)
        chan = self.chan
        current_dr = self.zs_divergence(chan.current_near_zs, self.allow_similar_zs,False, 3)
        if current_dr is not None:
            self.current_dr = current_dr
            self.current_dr_count = 10
        else:
            if self.current_dr_count is not None:
                self.current_dr_count -= 1
                current_dr = self.current_dr
                if self.current_dr_count == 0:
                    self.current_dr = None
        lower_dr = self.zs_divergence(chan.lower_near_zs, True, True, 1)
        if lower_dr is None and current_dr is None:
            return
        # 用于画图调试
        if lower_dr is not None:
            self.market_data.lower_ps = self.market_data.low if lower_dr.is_long else self.market_data.low
            self.market_data.lower_pst = "底" if lower_dr.is_long else "顶"

        if current_dr is not None:
            self.market_data.current_ps = self.market_data.low * Decimal("0.98") if current_dr.is_long else self.market_data.high * Decimal("1.02")
            self.market_data.current_pst = "底" if current_dr.is_long else "顶"

        if not self.have_position():
            if lower_dr is not None and current_dr is not None and current_dr == lower_dr:
                self.create_order(lower_dr, self.max_single_position)
                return
        else:
            if (lower_dr is not None and self.position.direction != lower_dr) or (current_dr is not None and current_dr != self.position.direction):
                self.close_position()
        # dr = lower_dr
        # if dr is not None:
        #     if self.have_position():
        #         if dr != self.position.direction:
        #             self.close_position()
        #         return
        #     self.create_order(dr)

    def zs_divergence(self, zs, allow_similar_zs=True, allow_dif_cross=True, divergence_type=1):
        """
        中枢背驰
        :param zs: 中枢
        :param allow_dif_cross: 是否允许dif跨越0轴
        :param allow_similar_zs: 是否允许类中枢
        :param divergence_type: 1: dif, 2: area, 3: dif|area  4: dif&area
        :return:
        """
        if zs is None:
            return None
        if len(zs.element_list) < 2 or (not allow_similar_zs and len(zs.element_list) < 4):
            return None
        last_ele = zs.element_list[-1]
        simulation_zs = zs.simulation()
        if simulation_zs is None:
            return None

        if not allow_similar_zs and simulation_zs.level == 0:
            return None
        if not self.is_breakout(simulation_zs, last_ele, allow_dif_cross):  # 未突破中枢
            return None

        out_klines = self.last_divergence_kline(simulation_zs)
        if out_klines is None:
            return None
        into_klines = simulation_zs.into_ele.klines
        dif_divergence = False
        area_divergence = False
        if divergence_type != 2:
            dif_divergence = self.dif_divergence(simulation_zs.is_up, into_klines, out_klines)
        if divergence_type!= 1:
            area_divergence = self.area_divergence(simulation_zs.is_up, into_klines, out_klines)
        if (divergence_type == 1 and dif_divergence) or \
                (divergence_type == 2 and area_divergence) or \
                (divergence_type == 3 and (dif_divergence or area_divergence)) or \
                (divergence_type == 4 and dif_divergence and area_divergence):
            return PositionSide.SHORT if zs.is_up else PositionSide.LONG
        return None

    def area_divergence(self, is_up, into_klines, out_klines):
        """
        中枢面积背驰
        :param is_up:  是否向上
        :param into_klines: 进入中枢的K线列表
        :param out_klines: 离开中枢的K线列表
        :return:
        """
        if is_up:
            pre_area = sum([x.m for x in into_klines if x.m > 0])
            area = sum([x.m for x in out_klines if x.m > 0])
            for i in range(1, len(out_klines)-2):
                if out_klines[i].m <= 0:
                    break
                area += out_klines[-i].m
        else:
            pre_area = abs(sum([x.m for x in into_klines if x.m < 0]))
            area = abs(sum([x.m for x in out_klines if x.m < 0]))
            for i in range(1, len(out_klines)-2):
                if out_klines[i].m >= 0:
                    break
                area += abs(out_klines[-i].m)

        return area / pre_area < self.divergence_rate

    def is_breakout(self, zs, last_union, allow_dif_cross):
        """
        突破中枢
        :param zs: 中枢
        :param last_union: 最后一笔
        :param allow_dif_cross: 允许dif跨越0轴
        :return:
        """
        into_ele = zs.into_ele
        out_ele = zs.out_ele
        if not allow_dif_cross and self.check_last_dif_is_cross(into_ele.klines, zs.is_up):
            return False
        if zs.is_up:
            if out_ele.high < zs.high or out_ele.klines[-1].low < zs.high:  # Out段没有新高 or 最后一跟K线还在里面
                return False
            if not last_union.is_up and last_union.low <= zs.high:  # 最后一笔向下 & 已经回落回中枢
                return False
            return True
        if out_ele.low > zs.low or out_ele.klines[-1].high > zs.low:  # Out段没有新低 or 最后一跟K线还在里面
            return False
        if last_union.is_up and last_union.high >= zs.low:  # 最后一笔向上 & 已经回升回中枢
            return False
        return True

    def last_divergence_kline(self, zs):
        """
        检查背驰点延迟是否满足
        :param zs:
        :return: 返回最后一组元素的k线列表
        """
        out_ele = zs.out_ele
        kl = out_ele.klines[:]
        if out_ele.next is not None:
            if out_ele.next.size > self.max_delay_k_num:
                return None
            for k in out_ele.next.klines:
                if k.timestamp > kl[-1].timestamp:
                    kl.append(k)
        idx = len(kl) - 1
        while idx >= 2:
            if (zs.is_up and 0 < kl[idx-2].m <= kl[idx-1].m <= kl[idx].m) or (not zs.is_up and kl[idx-2].m <= kl[idx-1].m <= kl[idx].m < 0):
                break
            if (zs.is_up and kl[idx].m <= 0) or (not zs.is_up and kl[idx].m >= 0):
                break
            idx -= 1
        if zs.is_up:
            if kl[-1].m < 0 or kl[-1].dif < 0:
                return None
            peak_idx = kl.index(max(kl[idx:], key=lambda x: x.m))
        else:
            if kl[-1].m > 0 or kl[-1].dif > 0:
                return None
            peak_idx = kl.index(min(kl[idx:], key=lambda x: x.m))
        if len(kl) - self.max_delay_k_num <= peak_idx <= len(kl) - 2:
            return kl

    def check_last_dif_is_cross(self, klines, is_up):
        """
        最高/低一段dif线是否穿过0轴
        :param klines: k线列表
        :param is_up: 方向是否向上， 向上找顶背驰， 向下找底背驰
        :return:
        """
        if is_up:
            max_k = max(klines, key=lambda x: x.dif)
            if max_k.dif < 0 or max_k.m < 0:
                return True
            idx = klines.index(max_k)
            for i in range(idx, 0, -1):
                if klines[i].m < 0 < klines[i].dif:
                    return False
            return True
        min_k = min(klines, key=lambda x: x.dif)

        if min_k.dif > 0 or min_k.m > 0:
            return True
        idx = klines.index(min_k)
        for i in range(idx, 0, -1):
            if klines[i].m > 0 > klines[i].dif:
                return False
        return True


    def dif_divergence(self, is_up, into_klines, out_klines):
        """
        需要计算dif背驰
        :param is_up: 是否向上
        :param into_klines: 进入中枢的K线列表
        :param out_klines: 离开中枢的K线列表
        :return:
        """
        if is_up:
            pre_max_dif = max([x.dif for x in into_klines])
            max_dif = max([x.dif for x in out_klines])
        else:
            pre_max_dif = abs(min([x.dif for x in into_klines]))
            max_dif = abs(min([x.dif for x in out_klines]))
        return (max_dif / pre_max_dif < self.divergence_rate) if pre_max_dif != 0 else False






if __name__ == '__main__':
    pass
