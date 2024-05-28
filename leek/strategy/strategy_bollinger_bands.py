#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/27 21:53
# @Author  : shenglin.li
# @File    : strategy_bollinger_bands.py
# @Software: PyCharm
import decimal
from collections import deque

import numpy as np

from leek.common import G, logger, StateMachine
from leek.strategy import *
from leek.strategy.common import *
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.trade.trade import Order, PositionSide, OrderType


class BollingerBandsStrategy(SymbolsFilter, CalculatorContainer, PositionRateManager, PositionDirectionManager,
                             FallbackTakeProfit, StopLoss, BaseStrategy):
    verbose_name = "布林带策略"
    """
    布林带策略
    核心思想：利用统计原理，求出股价的标准差及其信赖区间，从而确定股价的波动范围及未来走势，利用波带显示股价的安全高低价位
    风险: 单边行情, 不断突破刷新布林带上下轨
    """
    # 状态转换关系
    _state_transitions = {
        "DOWN_UP": {
            "UP": "UP_UP",
            "UNDER_CENTER": "DOWN_CENTER",
            "DOWN": "DOWN_DOWN",
        },
        "DOWN_CENTER": {
            "UP": "UP_UP",
            "ON_CENTER": "UP_CENTER",
            "DOWN": "DOWN_DOWN",
        },
        "DOWN_DOWN": {
            "UNDER_CENTER": "UP_DOWN",
            "ON_CENTER": "UP_CENTER",
            "UP": "UP_UP",
        },
        "UP_UP": {
            "ON_CENTER": "DOWN_UP",
            "UNDER_CENTER": "DOWN_CENTER",
            "DOWN": "DOWN_DOWN",
        },
        "UP_CENTER": {
            "UP": "UP_UP",
            "UNDER_CENTER": "DOWN_CENTER",
            "DOWN": "DOWN_DOWN",
        },
        "UP_DOWN": {
            "ON_CENTER": "UP_CENTER",
            "UP": "UP_UP",
            "DOWN": "DOWN_DOWN",
        }
    }

    def __init__(self, num_std_dev=2.0):
        """
        :param num_std_dev: 布林带上线轨标准差倍数，越大则布林带越宽
        """
        self.num_std_dev = decimal.Decimal(num_std_dev)

    def handle(self):
        """
        未持仓时，如果收盘价穿过布林线上轨，空，如果收盘价穿过布林线下轨，多
        有持仓时，
            如果收盘价穿过布林线上穿中轨回落，平多或者加空
            如果收盘价穿过布林线回踩中轨拉升，平空或者加多
        """
        if self.market_data.finish != 1:
            return
        calculator = self.calculator(self.market_data)
        upper_band, rolling_mean, lower_band = calculator.boll(self.market_data.close, num_std_dev=self.num_std_dev)
        if rolling_mean == 0:
            return

        price = self.market_data.close
        if not self.have_position():  # 无持仓
            if not self.enough_amount():
                return
            if price > upper_band and self.can_short():
                self.g.status = StateMachine("UP_UP", self._state_transitions)
                logger.info(
                    f"布林带开空[{self.market_data.symbol}]：price={price}, upper_band={upper_band}, rolling_mean={rolling_mean}, lower_band={lower_band}")
                self.create_order(PositionSide.SHORT, position_rate=self.max_single_position, memo="布林带开空")
            elif price < lower_band and self.can_long():
                self.g.status = StateMachine("DOWN_DOWN", self._state_transitions)
                logger.info(
                    f"布林带开多[{self.market_data.symbol}]：price={price}, upper_band={upper_band}, rolling_mean={rolling_mean}, lower_band={lower_band}")
                self.create_order(PositionSide.LONG, position_rate=self.max_single_position, memo="布林带开多")
        else:
            if price > upper_band:
                event = "UP"
            elif price > rolling_mean:
                event = "ON_CENTER"
            elif price > lower_band:
                event = "UNDER_CENTER"
            else:
                event = "DOWN"

            states = self.g.status.next(event)
            if len(states) < 3:
                return None
            # 回踩中轨继续向上 或 踩中轨拉回： 多
            if (states[-3] == "UP_CENTER" and states[-2] == "DOWN_CENTER" and states[-1] == "UP_CENTER") \
                    or (states[-3] == "DOWN_CENTER" and states[-2] == "UP_CENTER" and states[-1] == "UP_CENTER"):
                if self.is_long_position():
                    self.create_order(PositionSide.LONG, position_rate=self.max_single_position, memo="布林带加仓")
                else:
                    logger.info(f"布林带加仓[{self.market_data.symbol}]：price={price}, states={states}")
                    self.close_position("布林带平仓")
                return

            # 回踩中轨继续向下 或 上穿中轨后回落： 空
            if (states[-3] == "DOWN_CENTER" and states[-2] == "UP_CENTER" and states[-1] == "DOWN_CENTER") \
                    or (states[-3] == "UP_CENTER" and states[-2] == "DOWN_CENTER" and states[-1] == "DOWN_CENTER"):
                if self.is_long_position():
                    self.close_position("布林带平仓")
                else:
                    logger.info(f"布林带加仓[{self.market_data.symbol}]：price={price}, states={states}")
                    self.create_order(PositionSide.SHORT, position_rate=self.max_single_position, memo="布林带加仓")


class BollingerBandsV2Strategy(PositionRateManager, JustFinishKData, PositionDirectionManager, DynamicRiskControl, BaseStrategy):
    verbose_name = "布林带策略V2(MACD辅助)"
    """
    MACD 辅助boll判断
    参考资料：
        https://zhuanlan.zhihu.com/p/633238465
    """

    def __init__(self, window=20, num_std_dev="2.0", fast_period="14", slow_period="30", smoothing_period="10"):
        # boll
        self.window = int(window)
        self.num_std_dev = decimal.Decimal(num_std_dev)
        # macd
        self.fast_line_period = int(fast_period)
        self.slow_line_period = int(slow_period)
        self.average_moving_period = int(smoothing_period)

        self.macd_patience = 3

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": max(self.window, self.slow_line_period, self.average_moving_period)
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.market_data = market_data
            self._calculate()

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(
                maxlen=max(self.window, self.macd_patience, self.slow_line_period, self.average_moving_period))
        # 计算macd
        if self.market_data.finish != 1:
            if len(self.g.q) > 1:
                return list(self.g.q)[-1]
            return None

        self.g.q.append(self.market_data)
        data = list(self.g.q)

        if len(data) >= self.slow_line_period:
            self.market_data.ma_fast = sum([d.close for d in data[-self.fast_line_period:]]) / self.fast_line_period
            self.market_data.ma_slow = sum([d.close for d in data[-self.slow_line_period:]]) / self.slow_line_period
            self.market_data.dif = self.market_data.ma_fast - self.market_data.ma_slow

        if len(data) >= self.average_moving_period and data[-self.average_moving_period].dif is not None:
            self.market_data.dea = sum([d.dif for d in data[-self.average_moving_period:]]) / self.average_moving_period
            self.market_data.m = self.market_data.dif - self.market_data.dea

        # 计算boll
        if len(data) >= self.window:
            d = [d.close for d in data[-self.window:]]
            ma = sum(d) / self.window
            self.market_data.boll_upper_band = ma + self.num_std_dev * np.std(d)
            self.market_data.boll_lower_band = ma - self.num_std_dev * np.std(d)

        return data[-1] if len(data) > 0 else None

    def handle(self):
        """
        当期收盘价突破布林带上轨，且前n期内MACD出现金叉并无死叉，买入做多
        当期收盘价突破布林带下轨，且前n期内MACD出现死叉并无金叉，卖出做空
        """
        cur = self._calculate()
        data = list(self.g.q)
        if cur is None or len(data) < self.macd_patience or data[-self.macd_patience].m is None:
            return

        price = self.market_data.close
        if not self.have_position():
            if price > cur.boll_upper_band and self.can_long() and self.just_one_cross(
                    [d.m for d in data[-self.macd_patience:]], 1):  # 突破上轨
                self.create_order(PositionSide.LONG, position_rate=self.max_single_position, memo="布林带开多")
            elif price < cur.boll_lower_band and self.can_short() and self.just_one_cross(
                    [d.m for d in data[-self.macd_patience:]], 2):  # 突破下轨
                self.create_order(PositionSide.SHORT, position_rate=self.max_single_position, memo="布林带开空")

    def just_one_cross(self, data, cross_type=1):
        """
        判断是否只有一次交叉
        :param data: 数据
        :param cross_type: 1 金叉  2 死叉
        :return:
        """
        cross = 0
        for idx in range(len(data) - 1):
            if data[idx] * data[idx + 1] < 0:  # cross
                if cross > 0:
                    return False
                if data[idx] > 0 and cross_type == 1:  # 死叉
                    return False
                if data[idx] < 0 and cross_type == 2:  # 金叉
                    return False
                cross += 1
        return cross == 1


if __name__ == '__main__':
    print(issubclass(BollingerBandsStrategy, BaseStrategy))
