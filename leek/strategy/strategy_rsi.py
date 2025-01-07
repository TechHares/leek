#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/20 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
from collections import deque

from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.trade.trade import PositionSide


class RSIStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "RSI短线择时"

    """
    RSI衡量价格变动的速度和幅度.

    参考文献：
        https://zhuanlan.zhihu.com/p/661777573
    """

    def __init__(self, period=14, over_buy=70, over_sell=30):
        self.period = int(period)
        self.over_buy = int(over_buy)
        self.over_sell = int(over_sell)
        # self.smoothing_period = int(smoothing_period)

        self.mom_window = 100
        self.mom_long_threshold = [40, 100, 70]
        self.mom_short_threshold = [0, 60, 20]

        self.ibs_rsi_threshold = [40, 60]
        self.ibs_ibs_threshold = [25, 75]

        self.rsi_func = [self.classic_rsi, self.ibs_rsi, self.mom_rsi]

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(maxlen=max(self.period, self.mom_window))
        # 计算rsi
        data = list(self.g.q)
        cur_data = self.market_data
        if len(data) == 0:
            return
        cur_data.rsi_diff = cur_data.close - data[-1].close
        if len(data) < self.period or data[-self.period].rsi_diff is None:
            return

        if data[-1].avg_gain is None:
            gains = [max(0, d.rsi_diff) for d in data[-self.period:]]
            losses = [max(0, -d.rsi_diff) for d in data[-self.period:]]
            data[-1].avg_gain = sum(gains) / self.period
            data[-1].avg_loss = sum(losses) / self.period

        gain = max(0, cur_data.rsi_diff)
        loss = max(0, -cur_data.rsi_diff)

        cur_data.avg_gain = ((data[-1].avg_gain * (self.period - 1)) + gain) / self.period
        cur_data.avg_loss = ((data[-1].avg_loss * (self.period - 1)) + loss) / self.period
        cur_data.rsi = 100
        if cur_data.avg_loss != 0:
            cur_data.rsi = 100 - (100 / (1 + (cur_data.avg_gain / cur_data.avg_loss)))

        # 平滑RSI
        # q = [d.rs for d in data[-min(len(data), self.smoothing_period):] if d.rs is not None]
        # q.append(cur_data.rs)
        # cur_data.rsi = sum(q) / len(q)

        # 计算IBS
        cur_data.ibs = 0
        if cur_data.high != cur_data.low:
            cur_data.ibs = int((cur_data.close - cur_data.low) / (cur_data.high - cur_data.low) * 100)

        self.g.high_price = data[-1].high
        self.g.low_price = data[-1].low

    def handle(self):
        """
            三种开平仓模式
            一、经典模式: 在市场情绪处于相对低迷/高亢时入场 做反方向；RSI小于超卖超买
            二、做趋: 在市场的相对一致时入场 做同方向；RSI多头范围和多头动量条件都成立
            三、双指标: 市场表现弱/强势时入场市场出现上升/下降信号时离场

            当任一策略信号给出True值即入场做多，当所有策略信号都返回False值或达到止损目标时平仓离场
        """
        self._calculate()
        if self.market_data.finish == 1:
            self.g.q.append(self.market_data)
        if self.market_data.rsi is None:
            return
        if self.have_position():
            if all([c() for c in self.rsi_func]):
                self.close_position("RSI退出")
        else:
            print([c() == PositionSide.LONG for c in self.rsi_func])
            if self.can_long() and any([c() == PositionSide.LONG for c in self.rsi_func]):
                self.create_order(PositionSide.LONG, self.max_single_position)

            if self.can_short() and any([c() == PositionSide.SHORT for c in self.rsi_func]):
                self.create_order(PositionSide.SHORT, self.max_single_position)

    def classic_rsi(self):
        """
        1. RSI经典策略开仓
            超卖：RSI指标低于设定超卖阈值
            超买：RSI指标低于设定超买阈值
        2. 平仓
            a.突破上个bar高低点
            b.进入反向超X
        """
        if not self.have_position():
            if self.market_data.rsi < self.over_sell and self.can_long():
                return PositionSide.LONG

            if self.market_data.rsi > self.over_buy and self.can_short():
                return PositionSide.SHORT
        else:
            if self.market_data.close > self.g.high_price or self.market_data.close < self.g.low_price:
                return True

            if self.is_long_position():
                return self.market_data.rsi > self.over_buy
            else:
                return self.market_data.rsi < self.over_sell

        return None

    def mom_rsi(self):
        """
        1. RSI区域动量策略开仓
            头寸判断：使用历史(设定回看范围)rsi值计算趋势(如过去40个bar周期 rsi~[0, 60]空头, rsi~[40~100]多头)
            头寸动量：RSI的极值高/低点在N周期内大/小于阈值
            交易逻辑：
                当RSI多头范围和多头动量条件都成立时，开仓。
                当RSI多头范围和多头动量条件都不再成立时，平仓。
        """
        if not self.have_position():
            data = list(self.g.q)
            if len(data) < self.mom_window or data[-self.mom_window].rsi is None:
                return None
            data = data[-self.mom_window:]

            if self.can_long() and all(self.mom_long_threshold[0] < d.rsi < self.mom_long_threshold[1] for d in data) \
                    and any(d.rsi > self.mom_long_threshold[2] for d in data):
                return PositionSide.LONG

            if self.can_short() and all(self.mom_short_threshold[0] < d.rsi < self.mom_short_threshold[1] for d in data) \
                    and any(d.rsi < self.mom_short_threshold[2] for d in data):
                return PositionSide.SHORT
        else:
            data = list(self.g.q)[-self.mom_window:]
            if self.is_long_position():
                return not (all(
                    d.rsi is not None and self.mom_long_threshold[0] < d.rsi < self.mom_long_threshold[1] for d in data)
                            or any(d.rsi is not None and d.rsi > self.mom_long_threshold[2] for d in data))
            else:
                return not (all(
                    d.rsi is not None and self.mom_short_threshold[0] < d.rsi < self.mom_short_threshold[1] for d in
                    data)
                            or any(d.rsi is not None and d.rsi < self.mom_short_threshold[2] for d in data))
        return None

    def ibs_rsi(self):
        """
        1.RSI-IBS策略开仓
            RSI、IBS  双低开多， 双高开空
        2.平仓
            突破上个bar高低点
        """
        if not self.have_position():
            if self.can_long() and self.market_data.ibs < self.ibs_ibs_threshold[0] and self.market_data.rsi < \
                    self.ibs_rsi_threshold[0]:
                return PositionSide.LONG

            if self.can_short() and self.market_data.ibs > self.ibs_ibs_threshold[1] and self.market_data.rsi > \
                    self.ibs_rsi_threshold[1]:
                return PositionSide.SHORT
        else:
            if self.market_data.close > self.g.high_price or self.market_data.close < self.g.low_price:
                return True
            if self.is_long_position():
                return self.market_data.ibs > self.ibs_ibs_threshold[1] and self.market_data.rsi > \
                    self.ibs_rsi_threshold[1]
            else:
                return self.market_data.ibs < self.ibs_ibs_threshold[0] and self.market_data.rsi < \
                    self.ibs_rsi_threshold[0]
        return None


class RSIV2Strategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "RSI分仓择时"

    """
    1. 网格分仓思路
    2. RSI确定买卖点
    3. 网格分割线动态浮动
    4. 仓位使用预设生成， 首开仓位控制
    5. 特定条件下(极速波动)， 平大部分仓位锁定收益
    6. 开启条件、停止条件
    """

    def __init__(self):
        ...

    def _calculate(self):
        ...


    def handle(self):
        pass


if __name__ == '__main__':
    pass
