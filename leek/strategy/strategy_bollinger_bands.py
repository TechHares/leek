#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/27 21:53
# @Author  : shenglin.li
# @File    : strategy_bollinger_bands.py
# @Software: PyCharm
import decimal

from leek.common import G, logger, StateMachine
from leek.strategy import *
from leek.strategy.common import *
from leek.strategy.common.strategy_common import PositionRateManager
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
                logger.info(f"布林带开空[{self.market_data.symbol}]：price={price}, upper_band={upper_band}, rolling_mean={rolling_mean}, lower_band={lower_band}")
                self.create_order(PositionSide.SHORT, position_rate=self.max_single_position, memo="布林带开空")
            elif price < lower_band and self.can_long():
                self.g.status = StateMachine("DOWN_DOWN", self._state_transitions)
                logger.info(f"布林带开多[{self.market_data.symbol}]：price={price}, upper_band={upper_band}, rolling_mean={rolling_mean}, lower_band={lower_band}")
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


if __name__ == '__main__':
    print(issubclass(BollingerBandsStrategy, BaseStrategy))
