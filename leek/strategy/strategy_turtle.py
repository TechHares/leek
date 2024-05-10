#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/7 21:02
# @Author  : shenglin.li
# @File    : strategy_turtle.py
# @Software: PyCharm
from collections import deque
from datetime import datetime
from decimal import Decimal

from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionDirectionManager, PositionRateManager
from leek.trade.trade import PositionSide


class TurtleTradingStrategy(PositionRateManager, PositionDirectionManager, BaseStrategy):
    verbose_name = "海龟交易(原版)"
    """
    上轨 = Max（最高低，n）, n日最高价的最大值
    下轨 = Min（最低价，n）, n日最低价的最小值
    中轨 = (上轨+下轨)/2
    原则是定义好一个小单位（Unit），使得该仓位的预期价值波动与总净资产的1%对应。也就是说，如果买入了这1个小单位的资产，那当天该仓位的市值变动幅度不会超过总净资产的1%。
    TrueRange = Max(High−Low, High−PreClose, PreClose−Low)
    N = (前19日的N值之和+当时的TrueRange)/20
    Unit = (1%*Total_net)/N， Total_net就是总资产净值
    
    建仓的动作来自于趋势突破信号的产生。如果当前价格冲破上轨，就产生了一个买的建仓信号，如果当前价格跌破下轨，就产生了一个卖空的建仓信号
    初始建仓的大小 = 1个Unit
    
    如果开的底仓是多仓且资产的价格在上一次建仓（或者加仓）的基础上又上涨了0.5N，就再加一个Unit的多仓；
    如果开的底仓是空仓且资产的价格在上一次建仓（或者加仓）的基础上又下跌了0.5N，就再加一个Unit的空仓。
    
    如果开的底仓是多仓且资产的价格在上一次建仓（或者加仓）的基础上又下跌了2N，就卖出全部头寸止损；
    如果开的底仓是空仓且资产的价格在上一次建仓（或者加仓）的基础上又上涨了2N，就平掉全部的头寸止损。
    
    如果开的底仓是多仓且当前资产价格跌破了10日唐奇安通道的下轨，就清空所有头寸结束策略；
    如果开的底仓是空仓且当前资产价格升破了10日唐奇安通道的上轨，就清空所有头寸结束策略。
    """

    def __init__(self, open_channel=20, close_channel=10, true_range_window=20, expected_value="0.01",
                 add_position_rate="0.5", close_position_rate="2"):
        """
        :param open_channel: 唐奇安通道周期(开仓)
        :param close_channel: 唐奇安通道周期(平仓)
        :param true_range_window: 波动率平滑周期
        :param expected_value: 期望账户净值波动
        :param add_position_rate: 加仓阈值
        :param close_position_rate: 止损阈值
        """
        self.open_channel = int(open_channel)
        self.close_channel = int(close_channel)
        self.true_range_window = int(true_range_window)
        self.expected_value = Decimal(expected_value)
        self.add_position_rate = Decimal(add_position_rate)
        self.close_position_rate = Decimal(close_position_rate)

    def handle(self):
        pre = self._calculate()
        if pre is None:
            return
        if self.have_position():
            if pre.close_channel_lower is None:
                return

            if self.is_long_position():
                if self.market_data.close < max(pre.close_channel_lower, self.g.close_price):
                    self.close_position("多-头寸结束")
                    return
                if self.market_data.close > self.g.add_price:
                    self._add_position(PositionSide.LONG)
                    return
            else:
                if self.market_data.close > min(pre.close_channel_up, self.g.close_price):
                    self.close_position("空-头寸结束")
                    return
                if self.market_data.close < self.g.add_price:
                    self._add_position(PositionSide.SHORT)
                    return
        else:
            if not self.enough_amount():
                return

            if pre.open_channel_up is None:
                return

            if self.market_data.close > pre.open_channel_up and self.can_long():
                self._add_position(PositionSide.LONG)

            if self.market_data.close < pre.open_channel_lower and self.can_short():
                self._add_position(PositionSide.SHORT)

    def _calculate_channel(self, data, window):
        up = max([d.high for d in data[-window:]])
        lower = min([d.low for d in data[-window:]])
        return up, lower

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(maxlen=max(self.open_channel, self.close_channel, self.true_range_window))

        if self.market_data.finish != 1:
            if len(self.g.q) > 1:
                return list(self.g.q)[-1]
            return None

        self.g.q.append(self.market_data)
        data = list(self.g.q)
        if len(data) >= self.open_channel:
            data[-1].open_channel_up, data[-1].open_channel_lower = self._calculate_channel(data, self.open_channel)
        if len(data) >= self.close_channel:
            data[-1].close_channel_up, data[-1].close_channel_lower = self._calculate_channel(data, self.close_channel)

        if len(data) > 1:
            data[-1].tr = max(data[-1].high - data[-1].low, abs(data[-1].high - data[-2].close), abs(data[-2].close - data[-1].low))
        else:
            data[-1].tr = data[-1].high - data[-1].low

        if len(data) < self.true_range_window:
            data[-1].n = (sum([d.n for d in data[:-1]]) + data[-1].tr) / len(data)
        else:
            data[-1].n = (sum([d.n for d in data[-self.true_range_window:-1]]) + data[-1].tr) / self.true_range_window
        return data[-2] if len(data) > 1 else None

    def _add_position(self, side: PositionSide):
        if self.g.position_rate is None:
            self.g.position_rate = 0
        if self.g.position_rate >= self.max_single_position:
            return

        if not self.have_position():
            memo = "开仓"
        else:
            memo = "加仓"

        n = self.market_data.n
        price = self.market_data.close
        if side == PositionSide.LONG:
            self.g.add_price = price + self.add_position_rate * n
            self.g.close_price = price - self.close_position_rate * n
        else:
            self.g.add_price = price - self.add_position_rate * n
            self.g.close_price = price + self.close_position_rate * n

        rate = max(self.expected_value / n * price, self.max_single_position / 4)

        self.g.position_rate += rate
        self.create_order(side, rate, memo)

    def close_position(self, memo="", extend=None):
        self.g.position_rate = 0
        super().close_position(memo, extend)


class TurtleTrading1Strategy(TurtleTradingStrategy):
    verbose_name = "海龟交易V1"
    """
    在海龟交易原版基础上
    高低点使用影线一半， 减小插针对通道上下轨影响(回测中微略提升了在小币上的表现)
    """
    def __init__(self, half_needle=False):
        """
        :param half_needle: 唐奇安通道影线折半计算
        """
        x = str(half_needle).lower()
        self.half_needle = x in ["true", 'on', 'open', '1']

    def _calculate_channel(self, data, window):
        if not self.half_needle:
            return super()._calculate_channel(data, window)
        up = max([(d.high + max(d.close, d.open))/2 for d in data[-window:]])
        lower = min([(d.low + min(d.close, d.open))/2 for d in data[-window:]])
        return up, lower


class TurtleTrading2Strategy(TurtleTrading1Strategy):
    verbose_name = "海龟交易V2"
    """
    在海龟交易基础上
    引入价格变动过滤掉部分假震荡开仓信号  判定震荡提前结束头寸
    """

    def __init__(self, open_vhf_threshold="0.5", close_vhf_threshold="0.0"):
        """
        :param open_vhf_threshold: vhf开仓阈值(开仓)
        :param close_vhf_threshold: vhf平仓阈值(平仓)
        """
        self.open_vhf_threshold = Decimal(open_vhf_threshold)
        self.close_vhf_threshold = Decimal(close_vhf_threshold)

    def _calculate(self):
        r = super()._calculate()
        data = list(self.g.q)
        if len(data) >= 2:
            data[-1].diff = data[-1].close - data[-2].close
        if len(data) >= self.open_channel and data[-self.open_channel].diff is not None:
            h = abs(data[-1].close - data[-self.open_channel].close)
            v = sum([abs(x.diff) for x in data[-self.open_channel:]])
            data[-1].vhf = h / v if v != 0 else 0
        return r

    def _add_position(self, side: PositionSide):
        if not self.have_position() and self.market_data.vhf < self.open_vhf_threshold:  # 根据vhf 过滤掉部分假震荡开仓信号
            return
        super()._add_position(side)

    def close_position(self, memo="", extend=None):
        self.g.close_flag = True
        super().close_position(memo, extend)

    def handle(self):
        self.g.close_flag = False
        super().handle()
        if self.have_position() and not self.g.close_flag:
            if self.market_data.vhf is not None and self.market_data.vhf < self.close_vhf_threshold:
                self.close_position("波动率下降-平仓")
                self.g.close_flag = True


class TurtleTrading3Strategy(TurtleTrading2Strategy):
    verbose_name = "海龟交易V3"
    """
    在海龟交易V2基础上
    引入成交额加权移动均线结束头寸
    """

    def __init__(self, take_profit_period=10):
        """
        :param take_profit_period: vmma计算周期(平仓)
        """
        self.take_profit_period = int(take_profit_period)

    def _calculate(self):
        r = super()._calculate()
        data = list(self.g.q)
        if len(data) >= self.take_profit_period:
            data[-1].vmma = sum([x.amount/x.volume for x in data[-self.take_profit_period:]]) / self.take_profit_period
        return r

    def handle(self):
        super().handle()
        if self.have_position() and not self.g.close_flag:
            if self.market_data.vmma is not None and self.market_data.close < self.market_data.vmma:
                self.close_position("破vmma-平仓")
                self.g.close_flag = True


if __name__ == '__main__':
    pass
