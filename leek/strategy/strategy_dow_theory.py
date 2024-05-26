#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/10 19:43
# @Author  : shenglin.li
# @File    : strategy_super_trend.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

from leek.strategy import BaseStrategy
from leek.strategy.common import StopLoss
from leek.strategy.common.calculator import calculate_donchian_channel
from leek.strategy.common.strategy_common import PositionDirectionManager, PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, FallbackTakeProfit, DynamicRiskControl
from leek.trade.trade import PositionSide

"""
道氏理论
"""


class DowV1Strategy(JustFinishKData, PositionRateManager, PositionDirectionManager, DynamicRiskControl, BaseStrategy):
    verbose_name = "道氏理论(donchian channel+Lma)"
    """
    目标主要是在第二种中期趋势走势中获利，把顺长期趋势的中期行情定义为顺势，把逆长期趋势的中期行情定义为整理
    
    维克托·斯波朗迪使用趋势线、123 法则、2B 法则作为工具来应用道氏理论
    从易于量化的角度，我们使用长期均线、唐奇安通道、盈亏比为工具应用道氏理论。
    唐奇安通道对应中期趋势线。在多头市场中，使用唐奇安通道的下轨代替中期趋势线，在空头市场中，使用唐奇安通道的上轨代替中期趋势线。我们仍使用突破作为进场信号。
 
    对于中期整理行情，若长期趋势线的支持有效，则当价格上涨（下跌）到长期趋势线时及面临压力（支持），此时可能转变为震荡或中期顺势行情。而对于中期顺势行情，
    则可能沿着长期趋势方向有较大幅度的价格波动。可见对顺势和中期整理来说，其潜在的盈亏比是不同的，中期整理行情的潜在盈利区间更小。为了控制整理行情的交易次数，
    我们使用目标盈亏比的方法，当触发整理交易的开仓信号时，只有当潜在盈亏比大于目标盈亏比时，我们才进行交易。同样，根据顺势和整理的交易逻辑不同，我们还可以使用两种不同的参数的唐奇安通道。
    
    综上，可构造交易策略。假设 C、H、L 分别为收盘价、最高价、最低价，长期均线为 LMA，潜在盈亏比为 WinLossRate，目标盈亏比为 WinLossTarget，顺势交易的长短期唐奇安通道上下轨分别
    为 HiLongTrend ， LoLongTrend ，HiShortTrend ， LoShortTrend ， 整理交易的长短唐奇安通道为HiLongReverse，LoLongReverse，HiShortReverse，LoShortReverse
    公式分别为：
        LMA = mean(C, n)
        HiLongTrend = max(H, LongTrend)
        LoLongTrend = min(L, LongTrend)
        HiShortTrend = max(H, LongTrend)
        LoShortTrend = min(L, LongTrend)
        HiLongReverse = max(H, LongReverse)
        LoLongReverse = min(L, LongReverse)
        HiShortReverse = max(H, ShortReverse)
        LoShortReverse = min(L, ShortReverse)
        
    对于反转交易来说，使用开仓价格与相应的短期唐奇安通道为止损幅度，开仓价格与前一交易日长期均线之间的距离为潜在盈利幅度，计算相应的盈亏比，只
    有当盈亏比大于 WinLossTarget 时才进行交易。
    
    交易开平仓规则如下：
        对于顺势交易而言：当前一日收盘价大于长期均线(LMA)，且当日最高价突破顺势的长期唐奇安通道(HiLongTrend)时买入做多，以盘中触发价为准，平
    仓位置为顺势的短期唐奇安通道(LoShortTrend)；反之当前一日收盘价小于长期均线（LMA），且当日最低价向下突破顺势的长期唐奇安通道（LoLongTrend）
    时卖出做空，以盘中触发价为准，平仓位置顺势的短期唐奇安通道为（HiShortTrend）。
        对于中期整理交易而言：当前一日收盘价大于长期均线（LMA），且当日最低价向下突破中期整理的长期唐奇安通道（LoLongReverse），且盈亏比大于
    WinLossTarget时卖出做空，平仓位置为中期整理的短期唐奇安通 道为（HiShortReverse）；反之当前一日收盘价小于长期均线（LMA），且当日最高价
    向上突破中期整理的长期唐奇安通道（HiLongReverse），且盈亏比大于WinLossTarget 时卖出做空，平仓位置为中期整理的短期唐奇安通道为（LoShortReverse）。
    """

    def __init__(self, open_channel=20, close_channel=10, long_period=120, win_loss_target="2.0", half_needle=False,
                 trade_type=0):
        """
        :param open_channel: 唐奇安通道周期(开仓)
        :param close_channel: 唐奇安通道周期(平仓)
        :param long_period: 长期趋势线
        :param win_loss_target: 反转交易预期盈亏比
        :param half_needle: 影线折半处理
        :param trade_type: 交易类型 0 全部 1 顺势 2 反转
        """
        self.long_period = int(long_period)
        self.open_channel = int(open_channel)
        self.close_channel = int(close_channel)

        self.win_loss_target = Decimal(win_loss_target)
        x = str(half_needle).lower()
        self.half_needle = x in ["true", 'on', 'open', '1']

        # 0 全部 1 顺势 2 反转
        self.trade_type = int(trade_type)

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(maxlen=max(self.open_channel, self.close_channel, self.long_period))

        if self.market_data.finish != 1:
            if len(self.g.q) > 1:
                return list(self.g.q)[-1]
            return None

        self.g.q.append(self.market_data)
        data = list(self.g.q)
        if len(data) >= self.open_channel:
            data[-1].open_channel_up, data[-1].open_channel_lower = calculate_donchian_channel(data, self.open_channel,
                                                                                               self.half_needle)
        if len(data) >= self.close_channel:
            data[-1].close_channel_up, data[-1].close_channel_lower = calculate_donchian_channel(data,
                                                                                                 self.close_channel,
                                                                                                 self.half_needle)

        if len(data) >= self.long_period:
            data[-1].lma = sum([x.close for x in data[-self.long_period:]]) / self.long_period
        return data[-2] if len(data) > 1 else None

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": max(self.open_channel, self.close_channel, self.long_period)
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.market_data = market_data
            self._calculate()

    def handle(self):
        pre = self._calculate()
        if pre is None:
            return

        price = self.market_data.close
        if self.have_position():
            if self.market_data.finish == 1:
                self.g.handle_count += 1
            self.position.update_price(price)
            if self.position.value > self.position.quantity_amount and self.g.handle_count >= self.close_channel:
                target_price = self.position.avg_price * (1 + self.stop_loss_rate)
                if self.is_short_position():
                    target_price = self.position.avg_price * (1 - self.stop_loss_rate)
                if (self.is_long_position() and price < target_price) or (self.is_short_position() and price > target_price):
                    self.close_position("持仓周期超过平仓通道周期")
                    return
            if self.position.value < self.position.quantity_amount and self.g.handle_count >= self.open_channel:
                self.close_position("持仓周期超过开仓通道周期")
                return

            self.g.position_open_price_high = max(self.g.position_open_price_high, price)
            if self.g.can_add:  # 整理期开仓，突破加仓判断
                if self.is_long_position() and price > pre.lma:
                    self.g.can_add = None
                    self.create_order(PositionSide.LONG, self.max_single_position / 2, "整理-突破加仓(多)")
                if not self.is_long_position() and price < pre.lma:
                    self.g.can_add = None
                    self.create_order(PositionSide.SHORT, self.max_single_position / 2, "整理-突破加仓(空)")

            # 平仓判断
            if self.is_long_position():
                if pre.close_channel_lower and price < pre.close_channel_lower:  # 平多
                    self.close_position("平多")
                    return
            else:
                if pre.close_channel_up and price > pre.close_channel_up:  # 平空
                    self.close_position("平空")
                    return
        else:
            if pre.open_channel_up is None or pre.lma is None:
                return
            self.g.handle_count = 0
            self.g.position_open_price_high = price
            high = self.market_data.high if not self.half_needle else (self.market_data.high + max(self.market_data.open, price)) / 2
            if high > pre.open_channel_up and self.can_long():  # 做多判断
                if price < pre.lma and self.trade_type in [0, 2] and self._win_great_than_loss(price, pre, pre.close_channel_lower):  # 反转
                    self.g.can_add = True
                    self.create_order(PositionSide.LONG, self.max_single_position / 2, "反转-多")
                    return
                if price > pre.lma and self.trade_type in [0, 1]:  # 顺势
                    self.create_order(PositionSide.LONG, self.max_single_position, "顺势-多")
                    return

            low = self.market_data.low if not self.half_needle else (self.market_data.low + min(self.market_data.open, price)) / 2
            if low < pre.open_channel_lower and self.can_short():  # 做空判断
                if price > pre.lma and self.trade_type in [0, 2] and self._win_great_than_loss(price, pre, pre.close_channel_up):  # 反转
                    self.g.can_add = True
                    self.create_order(PositionSide.SHORT, self.max_single_position / 2, "反转-空")
                if price < pre.lma and self.trade_type in [0, 1]:  # 顺势
                    self.create_order(PositionSide.SHORT, self.max_single_position, "顺势-空")

    def _win_great_than_loss(self, price, pre, stop_loss_price):
        if stop_loss_price is None or price == stop_loss_price:
            return False
        win_loss_rate = (price - pre.lma) / (price - stop_loss_price)
        return abs(win_loss_rate) > self.win_loss_target

    def to_dict(self):
        p = self.position_manager.quantity_map
        position = [(k, "%s" % p[k].avg_price, "%s" % p[k].quantity_amount) for k in p]
        return {
            "position": position,
            "risk_control": [(k, "%s" % self.risk_container[k].stop_loss_price) for k in self.risk_container],
            "value": "%s" % self.position_manager.get_value()
        }


if __name__ == '__main__':
    pass
