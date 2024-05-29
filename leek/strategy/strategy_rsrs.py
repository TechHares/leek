#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/17 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
from leek.strategy import BaseStrategy
from leek.strategy.common.decision import STDecisionNode
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl
from leek.t import RSRS
from leek.trade.trade import PositionSide


class RSRSStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, BaseStrategy):
    verbose_name = "阻力支撑相对强度择时"

    """
    阻力支撑相对强度(rsrs)


    参考文献：
        https://mp.weixin.qq.com/s?__biz=MzkyODI5ODcyMA==&mid=2247485087&idx=1&sn=f42bcb657ce82654a537194992787157
        https://mp.weixin.qq.com/s?__biz=MzkyODI5ODcyMA==&mid=2247485225&idx=1&sn=dba12368183359f98f7b0f60ea6a38a4
        https://mp.weixin.qq.com/s?__biz=MzkyODI5ODcyMA==&mid=2247483898&idx=1&sn=d792431094001b4e64360a901b92e6bf&scene=21
        
        https://www.joinquant.com/view/community/detail/1f0faa953856129e5826979ff9b68095
        https://www.joinquant.com/view/community/detail/32b60d05f16c7d719d7fb836687504d6
        https://www.joinquant.com/view/community/detail/539e74507dbf571f2be21d8fa4ebb8e6
    """

    def __init__(self, window=18, static_window=600):
        self.rsrs = RSRS(window, static_window)

    def handle(self):
        t = self.market_data
        t.beta, t.std_score, t.mdf_std_score, t.rsk_std_score = self.rsrs.update(self.market_data)
        if self.market_data.rsk_std_score is None:
            return
        s = 0.7
        if not self.have_position():
            if self.market_data.rsk_std_score > s:
                self.create_order(PositionSide.LONG, self.max_single_position)
        else:
            if self.market_data.rsk_std_score < -0.3:
                self.close_position("z_score小于 -%s" % s)

        # if self.market_data.mdf_std_score is None:
        #     return
        # s = 0.7
        # if not self.have_position():
        #     if self.market_data.mdf_std_score > s:
        #         self.create_order(PositionSide.LONG, self.max_single_position)
        # else:
        #     if self.market_data.mdf_std_score < -s:
        #         self.close_position("z_score小于 -%s" % s)

        # if self.market_data.std_score is None:
        #     return
        # s = 0.7
        # if not self.have_position():
        #     if self.market_data.std_score > s:
        #         self.create_order(PositionSide.LONG, self.max_single_position)
        # else:
        #     if self.market_data.std_score < -s:
        #         self.close_position("z_score小于 -%s" % s)

        # if self.market_data.beta is None:
        #     return
        # if not self.have_position():
        #     if self.market_data.beta > 1:
        #         self.create_order(PositionSide.LONG, self.max_single_position)
        #     if self.market_data.beta < 0.7:
        #         self.create_order(PositionSide.SHORT, self.max_single_position)
        # else:
        #     if self.market_data.beta < 1:
        #         self.close_position("斜率小于0.8")


if __name__ == '__main__':
    pass
