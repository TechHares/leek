#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/27 21:53
# @Author  : shenglin.li
# @File    : strategy_bollinger_bands.py
# @Software: PyCharm
import decimal

from leek.common import G, Calculator, logger, StateMachine
from leek.strategy import *
from leek.strategy.strategy_common import StopLoss
from leek.trade.trade import Order, PositionSide, OrderType


class BollingerBandsStrategy(SymbolsFilter, CalculatorContainer, PositionDirectionManager, FallbackTakeProfit,
                             StopLoss, PositionRollingCalculator, BaseStrategy):
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

    def handle(self, market_data: G) -> Order:
        """
        未持仓时，如果收盘价穿过布林线上轨，空，如果收盘价穿过布林线下轨，多
        有持仓时，
            如果收盘价穿过布林线上穿中轨回落，平多或者加空
            如果收盘价穿过布林线回踩中轨拉升，平空或者加多
        :param market_data: 数据
        :return: 交易指令
        """
        calculator = self.calculator(market_data)
        upper_band, rolling_mean, lower_band = calculator.boll(market_data.close if market_data.finish != 1 else None,
                                                               num_std_dev=self.num_std_dev)
        if rolling_mean == 0:
            return None

        if not self.have_position(market_data):  # 无持仓
            if market_data.close > upper_band and self.is_short():
                self.g.status = StateMachine("UP_UP", self._state_transitions)
                side = PositionSide.SHORT
            elif market_data.close < lower_band and self.is_long():
                self.g.status = StateMachine("DOWN_DOWN", self._state_transitions)
                side = PositionSide.LONG
            else:
                return None

            amount = self.calculate_buy_amount("0.3", market_data.symbol, "0.8")
            if amount <= 0:
                return None
            order = self._create_order(market_data, side, amount)
            logger.info(f"布林带开仓：{order}")
            return order
        else:
            if market_data.close > upper_band:
                event = "UP"
            elif market_data.close > rolling_mean:
                event = "ON_CENTER"
            elif market_data.close > lower_band:
                event = "UNDER_CENTER"
            else:
                event = "DOWN"

            return self.deal_position(market_data, event)

    def deal_position(self, market_data: G, event):
        states = self.g.status.next(event)
        if len(states) < 3:
            return None
        # 回踩中轨继续向上 或 踩中轨拉回： 多
        if (states[-3] == "UP_CENTER" and states[-2] == "DOWN_CENTER" and states[-1] == "UP_CENTER") \
                or (states[-3] == "DOWN_CENTER" and states[-2] == "UP_CENTER" and states[-1] == "UP_CENTER"):
            if self.position_is_long(market_data):
                amount = self.calculate_buy_amount("0.3", market_data.symbol, "0.8")
                if amount <= 0:
                    return None
                order = self._create_order(market_data, PositionSide.LONG, amount)
                logger.info(f"布林带加仓：{order}")
                return order
            else:
                order = self._close_position(market_data)
                logger.info(f"布林带平仓：{order}")
                return order

        # 回踩中轨继续向下 或 上穿中轨后回落： 空
        if (states[-3] == "DOWN_CENTER" and states[-2] == "UP_CENTER" and states[-1] == "DOWN_CENTER") \
                or (states[-3] == "UP_CENTER" and states[-2] == "DOWN_CENTER" and states[-1] == "DOWN_CENTER"):
            if self.position_is_long(market_data):
                order = self._close_position(market_data)
                logger.info(f"布林带平仓：{order}")
                return order
            else:
                amount = self.calculate_buy_amount("0.3", market_data.symbol, "0.8")
                if amount <= 0:
                    return None
                order = self._create_order(market_data, PositionSide.SHORT, amount)
                logger.info(f"布林带加仓：{order}")
                return order


if __name__ == '__main__':
    print(issubclass(BollingerBandsStrategy, BaseStrategy))
