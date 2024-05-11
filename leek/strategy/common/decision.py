#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/9 20:21
# @Author  : shenglin.li
# @File    : decision.py
# @Software: PyCharm
from abc import ABCMeta, abstractmethod
from collections import deque
from decimal import Decimal

import numpy as np


class DecisionNode(metaclass=ABCMeta):
    """
    决策节点: 简单技术指标开/平仓抽象
    """

    def __init__(self, max_length=1):
        self.data = deque(maxlen=max_length)

    def open_long(self, market_data) -> bool:
        self.data.append(market_data)
        data = list(self.data)
        self._computed(data)
        return self._open_long(data)

    def close_long(self, market_data) -> bool:
        self.data.append(market_data)
        data = list(self.data)
        self._computed(data)
        return self._close_long(data)

    @abstractmethod
    def _open_long(self, data) -> bool:
        pass

    @abstractmethod
    def _close_long(self, data) -> bool:
        pass

    @abstractmethod
    def _computed(self, data):
        pass

    def evaluation(self, evaluation_data, fee_rate=Decimal(0)):
        trade_count = 0
        profit = Decimal("1")
        position_price = None
        for d in evaluation_data:
            if position_price is None:
                if self.open_long(d):
                    position_price = d.close
            else:
                if self.close_long(d):
                    trade_count += 1
                    profit = profit * d.close / position_price - 2 * fee_rate
                    position_price = None
        if position_price is not None:
            trade_count += 1
            profit = profit * evaluation_data[-1].close / position_price
        return trade_count, profit

    def copy_data(self, ins):
        for d in list(self.data):
            ins.data.append(d)
            data = list(ins.data)
            ins._computed(data)


class MADecisionNode(DecisionNode):
    """
    双均线决策 计算方式：SMA
    """

    def __init__(self, fast_period=5, slow_period=20):
        DecisionNode.__init__(self, max_length=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _computed(self, data):
        if len(data) < self.slow_period:
            return
        data[-1].ma_fast_period = sum([d.close for d in data[-self.fast_period:]]) / self.fast_period
        data[-1].ma_slow_period = sum([d.close for d in data[-self.slow_period:]]) / self.slow_period

    def _open_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.ma_slow_period is None:
            return False

        if cur_data.ma_fast_period < cur_data.ma_slow_period:
            return False
        if cur_data.close < cur_data.ma_fast_period:
            return False
        if len(data) < 3 or data[-3].ma_slow_period is None:  # 最近3天需要有数据
            return False

        # 1.快线连续拉升 2.慢线连续拉升 3.快线增幅逐渐增大
        return data[-1].ma_fast_period > data[-2].ma_fast_period > data[-3].ma_fast_period and \
               data[-1].ma_slow_period > data[-2].ma_slow_period > data[-3].ma_slow_period and \
               data[-1].ma_fast_period - data[-2].ma_fast_period > data[-2].ma_fast_period - data[-3].ma_fast_period

    def _close_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.ma_slow_period is None:
            return False

        if data[-1].ma_fast_period < data[-2].ma_fast_period < data[-3].ma_fast_period:  # 快线连续下降
            return True
        if data[-1].ma_slow_period < data[-2].ma_slow_period < data[-3].ma_slow_period:  # 慢线连续下降
            return True
        if cur_data.ma_fast_period < cur_data.ma_slow_period:  # 死叉
            return True
        if cur_data.close < cur_data.ma_fast_period and data[-2].close < data[-2].ma_fast_period:  # 破快线两周期不收回
            return True
        if cur_data.close < cur_data.ma_slow_period:
            return True
        return False


class MACDDecisionNode(DecisionNode):
    """
    MACD决策 均线计算方式：SMA
    """

    def __init__(self, fast_period=12, slow_period=26, moving_period=9):
        DecisionNode.__init__(self, max_length=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.moving_period = moving_period

    def _computed(self, data):
        if len(data) < self.moving_period:
            return
        cur_data = data[-1]
        cur_data.macd_fast_period = sum([d.close for d in data[-self.fast_period:]]) / self.fast_period
        cur_data.macd_slow_period = sum([d.close for d in data[-self.slow_period:]]) / self.slow_period
        cur_data.macd_dif = cur_data.macd_fast_period - cur_data.macd_slow_period
        if data[-self.moving_period].macd_dif is None:
            return
        cur_data.macd_dea = sum([d.macd_dif for d in data[-self.moving_period:]]) / self.moving_period
        cur_data.macd_m = cur_data.macd_dif - cur_data.macd_dea

    def _open_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.macd_m is None or len(data) < 4 or data[-4].macd_m is None:
            return False

        # diff线没有逐步扩大
        if not data[-1].macd_dif > data[-2].macd_dif > data[-3].macd_dif:
            return False

        return cur_data.macd_dif > cur_data.macd_dea > 0 and cur_data.macd_m > 0 \
               and cur_data.macd_m > data[-2].macd_m

    def _close_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.macd_m is None:
            return False
        return cur_data.macd_dif < cur_data.macd_dea or cur_data.macd_m < 0 or cur_data.macd_dif < 0


class RSIDecisionNode(DecisionNode):
    """
    RSI决策 评估过去一段时间内的价格变动速度和变动幅度，以判断超买或超卖的条件
    """

    def __init__(self, period=14, over_buy=70, over_sell=30):
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.over_buy = over_buy
        self.over_sell = over_sell

    def _computed(self, data):
        cur_data = data[-1]
        if len(data) < 2:
            cur_data.rsi_diff = 0
            return
        cur_data.rsi_diff = cur_data.close - data[-2].close
        if len(data) < self.period:
            return

        rsi_gain = [d.rsi_diff for d in data if d.rsi_diff > 0]
        rsi_gain_sum = sum(rsi_gain)
        rsi_loss = [d.rsi_diff for d in data if d.rsi_diff < 0]
        rsi_loss_sum = abs(sum(rsi_loss))
        if len(rsi_gain) == 0 or rsi_gain_sum == 0:
            cur_data.rsi = 0
            return

        if len(rsi_loss) == 0 or rsi_loss_sum == 0:
            cur_data.rsi = 100
            return

        cur_data.rsi = 100 - int(100 / (1 + (rsi_gain_sum / len(rsi_gain)) / (rsi_loss_sum / len(rsi_loss))))

    def _open_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.rsi is None or data[-2].rsi is None:
            return False

        return self.over_sell > cur_data.rsi > data[-2].rsi

    def _close_long(self, data) -> bool:
        if data[-1].rsi is None or data[-4].rsi is None:
            return False

        return data[-1].rsi < data[-2].rsi or \
               (data[-1].rsi > self.over_buy and data[-2].rsi > self.over_buy
                and data[-3].rsi > self.over_buy and data[-4].rsi > self.over_buy)


class VolumeDecisionNode(DecisionNode):
    """
    量比决策 成交量指标显示在特定时间段内交易的票据数量 款慢均线平滑
    """

    def __init__(self, fast_period=20, slow_period=30):
        DecisionNode.__init__(self, max_length=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _computed(self, data):
        if len(data) < self.slow_period:
            return
        data[-1].vol_fast_period = sum([d.amount for d in data[-self.fast_period:]]) / self.fast_period
        data[-1].vol_slow_period = sum([d.amount for d in data[-self.slow_period:]]) / self.slow_period

    def _open_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.vol_slow_period is None:
            return False

        if len(data) < 3 or data[-3].vol_fast_period is None:  # 最近3天需要有数据
            return False

        # 快线连续拉升 快线>慢线
        return data[-1].vol_fast_period > data[-2].vol_fast_period > data[-3].vol_fast_period \
               and cur_data.vol_fast_period > cur_data.vol_slow_period

    def _close_long(self, data) -> bool:
        cur_data = data[-1]
        if cur_data.vol_slow_period is None:
            return False
        return cur_data.vol_fast_period < cur_data.vol_slow_period


class BollDecisionNode(DecisionNode):
    """
    布林带决策，由三条线组成：中间是简单移动平均线 (SMA)，上下两条线则是SMA的标准差。布林带可以帮助投资者评估市场的波动性，并识别潜在的买卖点。
    """

    def __init__(self, period=20, num_std_devs=2):
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.num_std_devs = num_std_devs

    def _computed(self, data):
        cur_data = data[-1]
        if len(data) < self.period:
            return
        cur_data.boll_ma = sum([d.close for d in data[-self.period:]]) / self.period
        rolling_std = np.std([x.close for x in data])
        cur_data.boll_std = rolling_std
        # 计算上轨和下轨
        cur_data.boll_upper_band = cur_data.boll_ma + (rolling_std * self.num_std_devs)
        cur_data.boll_lower_band = cur_data.boll_ma - (rolling_std * self.num_std_devs)

    def _open_long(self, data) -> bool:
        if data[-1].boll_lower_band is None:
            return False

        if len(data) < 3 or data[-3].boll_lower_band is None:  # 最近3天需要有数据
            return False

        # 下轨拉升
        return data[-1].boll_lower_band > data[-2].boll_lower_band > data[-3].boll_lower_band \
               and data[-1].close > data[-1].boll_lower_band

    def _close_long(self, data) -> bool:
        if data[-1].boll_lower_band is None:
            return False

        return data[-1].boll_upper_band < data[-1].close or \
               data[-1].boll_upper_band < data[-2].boll_upper_band < data[-3].boll_upper_band


class StochasticDecisionNode(DecisionNode):
    """
    随机指标 (Stochastic Oscillator)
    随机指标是一种动量指标，比较当前价格与过去一段时间内的价格范围。它尤其适用于识别潜在的反转点。
    """

    def __init__(self, period=14, moving_period=3, over_buy=70, over_sell=30):
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.moving_period = moving_period
        self.over_buy = over_buy
        self.over_sell = over_sell
        self.alpha = 2 / (self.moving_period + 1)

    def _computed(self, data):
        if len(data) < self.period:
            return
        data[-1].stc_high = max([d.high for d in data])
        data[-1].stc_low = min([d.low for d in data])
        data[-1].stc_k = int(
            (data[-1].close - data[-1].stc_low) / (data[-1].stc_high - data[-1].stc_low) * 100)
        if data[-2].stc_d is None:
            data[-1].stc_d = data[-1].stc_k
        else:
            data[-1].stc_d = self.alpha * data[-1].stc_k + (1 - self.alpha) * data[-2].stc_d

    def _open_long(self, data) -> bool:
        if data[-1].stc_k is None or data[-1].stc_d is None:
            return False

        return self.over_sell > data[-1].stc_k > data[-1].stc_d

    def _close_long(self, data) -> bool:
        if data[-1].stc_k < data[-1].stc_d:
            return True

        if len(data) < 3 or data[-3].stc_k is None:  # 最近3天需要有数据
            return False

        return data[-1].stc_k < data[-2].stc_k < data[-3].stc_k or \
               self.over_buy < data[-1].stc_d


class OBVDecisionNode(DecisionNode):
    """
    能量潮决策 (On-Balance Volume, OBV)
    OBV是通过将每天的成交量加减到一个累计总数上来计算的，价格上涨时的成交量为正值，价格下跌时的成交量为负值。OBV可以帮助识别资金流向。
    """

    def __init__(self, fast_period=5, slow_period=10):
        DecisionNode.__init__(self, max_length=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _computed(self, data):
        if len(data) < 2:
            data[-1].obv = 0
            return
        data[-1].obv = data[-2].obv + (data[-1].close - data[-2].close) * data[-1].volume
        if len(data) < self.slow_period:
            return

        data[-1].obv_fast_period = sum([d.obv for d in data[-self.fast_period:]]) / self.fast_period
        data[-1].obv_slow_period = sum([d.obv for d in data[-self.slow_period:]]) / self.slow_period

    def _open_long(self, data) -> bool:
        if data[-1].obv_slow_period is None:
            return False

        if len(data) < 3 or data[-3].obv_slow_period is None:
            return False

        return data[-1].obv_fast_period > data[-1].obv_slow_period and \
               (data[-3].obv_fast_period < data[-2].obv_fast_period < data[-1].obv_fast_period)

    def _close_long(self, data) -> bool:
        if data[-1].obv_slow_period is None:
            return False

        if data[-3].obv_slow_period is None:
            return False

        return data[-1].obv_fast_period < data[-1].obv_slow_period and \
               (data[-3].obv_fast_period > data[-2].obv_fast_period > data[-1].obv_fast_period)


class PSYDecisionNode(DecisionNode):
    """
    心理线决策 (Psychological Line, PSY)
    PSY是根据投资者在一段时间内看多或看空的心理状态来计算的。它通常用于评估市场的极端情绪，可能预示着即将到来的趋势反转。
    """

    def __init__(self, period=20, over_buy=75, over_sell=25):
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.over_buy = over_buy
        self.over_sell = over_sell

    def _computed(self, data):
        data[-1].psy_d = 0
        if len(data) < 2:
            return
        if list(data)[-2].close < data[-1].close:
            data[-1].psy_d = 1

        if len(data) == self.period:
            data[-1].psy = int(sum([d.psy_d for d in data]) / self.period * 100)

    def _open_long(self, data) -> bool:
        return data[-1].psy is not None and self.over_sell > data[-1].psy

    def _close_long(self, data) -> bool:
        return data[-1].psy is not None and self.over_buy < data[-1].psy


class PVTDecisionNode(DecisionNode):
    """
    价量趋势决策（Price Volume Trend, PVT）
    PVT是一种结合了价格变动和成交量的技术分析工具，用于衡量市场趋势的强度和交易活动。PVT的计算考虑了价格变动的方向和成交量的变化，从而提供了市场动力的一个综合指标。
    """

    def __init__(self, fast_period=5, slow_period=10):
        DecisionNode.__init__(self, max_length=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _computed(self, data):
        if len(data) < 2:
            data[-1].pvt = 0
            return
        data[-1].pvt = data[-2].pvt + (data[-1].close - data[-2].close) / data[-2].close * data[-1].volume
        if len(data) < self.slow_period:
            return

        data[-1].pvt_fast_period = sum([d.pvt for d in data[-self.fast_period:]]) / self.fast_period
        data[-1].pvt_slow_period = sum([d.pvt for d in data[-self.slow_period:]]) / self.slow_period

    def _open_long(self, data) -> bool:
        if data[-1].pvt_slow_period is None:
            return False

        if len(data) < 3 or data[-3].pvt_slow_period is None:
            return False

        return data[-1].pvt_fast_period > data[-1].pvt_slow_period and \
               (data[-3].pvt_fast_period < data[-2].pvt_fast_period < data[-1].pvt_fast_period)

    def _close_long(self, data) -> bool:
        if data[-1].pvt_slow_period is None:
            return False

        if data[-3].pvt_slow_period is None:
            return False

        return data[-1].pvt_fast_period < data[-1].pvt_slow_period and \
               (data[-3].pvt_fast_period > data[-2].pvt_fast_period > data[-1].pvt_fast_period)


class SMIIODecisionNode(DecisionNode):
    """
    SMI决策
    SMI遍历性指标（SMI Ergodic Indicator/Oscillator）是一种结合了趋势跟踪和动量测量的技术分析工具。
    """

    def __init__(self, fast_period=5, slow_period=20, sigma_period=5):
        DecisionNode.__init__(self, max_length=max(slow_period, sigma_period))
        self.sigma_period = sigma_period
        self.fast_period = fast_period
        self.slow_period = slow_period

        self.dead_cross_smiio_erg = 0

    def _computed(self, data):
        if len(data) < 2:
            data[-1].smiio_diff = 0
            data[-1].smiio_fast_pc = 0
            data[-1].smiio_slow_pc = 0
            data[-1].smiio_erg = 0
            data[-1].smiio_sig = 0
            data[-1].smiio_osc = 0
            return
        data[-1].smiio_diff = data[-1].close - data[-2].close

        fast_alpha = Decimal(2 / (self.fast_period + 1))
        data[-1].smiio_fast_pc = fast_alpha * data[-1].smiio_diff + (1 - fast_alpha) * data[-2].smiio_fast_pc
        slow_alpha = Decimal(2 / (self.slow_period + 1))
        data[-1].smiio_slow_pc = slow_alpha * data[-1].smiio_diff + (1 - slow_alpha) * data[-2].smiio_slow_pc
        if data[-1].smiio_slow_pc == 0:
            data[-1].smiio_erg = 0
            data[-1].smiio_sig = 0
            data[-1].smiio_osc = 0
            return
        # Indicator
        data[-1].smiio_erg = int((data[-1].smiio_fast_pc - data[-1].smiio_slow_pc) / data[-1].smiio_slow_pc * 100)
        # Signal
        tsi_alpha = Decimal(2 / (self.sigma_period + 1))
        data[-1].smiio_sig = tsi_alpha * data[-1].smiio_erg + (1 - tsi_alpha) * data[-2].smiio_erg
        # Oscillator
        data[-1].smiio_osc = data[-1].smiio_erg - data[-1].smiio_sig

    def _open_long(self, data) -> bool:
        d = data[-1]
        return d.smiio_osc > 0 and d.smiio_sig > 0 and d.smiio_erg > data[-2].smiio_erg

    def _close_long(self, data) -> bool:
        d = data[-1]
        return d.smiio_erg < d.smiio_sig < 0


class STDecisionNode(DecisionNode):
    """
    超级趋势（SuperTrend）
    用于确定市场的长期趋势，并生成交易信号。它结合了平均真实范围（ATR）和移动平均线（通常是简单移动平均线，SMA）的概念，创建一个动态的支撑和阻力线
    """

    def __init__(self, period=10, factory=3):
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.factory = factory
        self.trend = 1

    def _computed(self, data):
        d = data[-1]
        if len(data) < 2:
            d.st_tr = d.high - d.low
            return

        d.st_tr = max(d.high - d.low, abs(d.high - data[-2].close), abs(d.low - data[-2].close))
        if len(data) < self.period:
            return
        d.st_atr = sum([d.st_tr for d in data]) / self.period
        # basic 可以选择 sma/close/avg(high+low)/avg_price 此处选close
        basic = d.close
        d.st_up = basic + self.factory * d.st_atr
        d.st_low = basic - self.factory * d.st_atr

        if data[-2].st_up is None or data[-2].st_low is None:
            d.st_trend = basic
            return

        if basic > data[-2].st_trend:
            self.trend = 1
        if basic < data[-2].st_trend:
            self.trend = -1

        if self.trend == 1:
            d.st_trend = max(d.st_low, data[-2].st_trend)
        if self.trend == -1:
            d.st_trend = min(d.st_up, data[-2].st_trend)

    def _open_long(self, data) -> bool:
        if len(data) < 2 or data[-2].st_trend is None:
            return False
        return self.trend == 1 and data[-1].close > data[-1].st_trend and data[-2].close > data[-2].st_trend

    def _close_long(self, data) -> bool:
        if data[-1].st_trend is None:
            return False
        return self.trend == -1 or data[-1].close < data[-1].st_trend


class MomDecisionNode(DecisionNode):
    """
    动量决策（Momentum Indicator）
    通过测量价格变化的速率来评估市场趋势的强度和潜在的反转信号，识别价格趋势是否正在加速、减速或维持现有速度。
    """

    def __init__(self, period=10, price_type=1):
        """
        :param period: 周期
        :param price_type: 计算值类型 1：收盘价 2：最高价 3：最低价 4：开盘价 5：平均价 6：avg(high+low) 7：avg(high+low+close) 8：avg(open+high+low+close)
        """
        DecisionNode.__init__(self, max_length=period)
        self.period = period
        self.price_type = price_type

    def get_price(self, d):
        if self.price_type == 2:
            return d.high
        elif self.price_type == 3:
            return d.low
        elif self.price_type == 4:
            return d.open
        elif self.price_type == 5:
            return d.amount / d.volume
        elif self.price_type == 6:
            return (d.high + d.low) / 2
        elif self.price_type == 7:
            return (d.high + d.low + d.close) / 3
        elif self.price_type == 8:
            return (d.open + d.high + d.low + d.close) / 4
        return d.close

    def _computed(self, data):
        if len(data) < self.period:
            return

        data[-1].momentum = self.get_price(data[-1]) - self.get_price(data[-self.period])

    def _open_long(self, data) -> bool:
        return data[-1].momentum is not None and data[-1].momentum > 0

    def _close_long(self, data) -> bool:
        return data[-1].momentum is not None and data[-1].momentum < 0


if __name__ == '__main__':
    pass
