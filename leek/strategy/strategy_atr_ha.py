#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/2/5 16:43
# @Author  : shenglin.li
# @File    : strategy_atr_ha.py
# @Software: PyCharm
import datetime

import pandas as pd

from leek.strategy import *
from leek.strategy.common import *
from leek.trade.trade import PositionSide


class ATRHeikinAshiStrategy(SymbolsFilter, AtrStopLoss, PositionDirectionManager, BaseStrategy):
    verbose_name = "ATR混合策略"
    """
    ATR（Average True Range）: 用于衡量金融资产价格波动性的技术指标，通常用于确定市场的波动性和价格变动的幅度。 
    Heikin-Ashi: 用于突出和明朗当前的趋势
    stochastics: 平滑随机指标， 判断短期超买/卖
    核心思想：ATR 判断整理期结束，Heikin-Ashi 判断趋势
    """

    def __init__(self):
        # self.over_buy = 75
        # self.over_sell = 25
        self.position_rate = 0.5

    def handle(self):
        calculator = self.calculator(self.market_data)
        df = calculator.heikin_ashi()
        if not self.have_position():  # 寻找开仓点
            if df is None:
                return
            atr = calculator.atr()
            if atr is None or not atr[-1] > atr[-2] > atr[-3]:
                return
            side = self.trend_from_heikin_ashi(df)
            df = calculator.stochastics()
            side = self.trend_check_stochastics(df, side)
            if not self.can_do(side):
                return
            self.create_order(side, position_rate=self.position_rate, memo="ATR混合策略开仓")
        else:  # 寻找止盈/损点
            cur_ha = df.iloc[-1]
            if self.is_long_position():
                if cur_ha["side"] == 1 and cur_ha["ha_high"] - cur_ha["ha_close"] > 2 * (cur_ha["ha_close"] - cur_ha["ha_low"]):  # 超长上影线
                    self.close_position(memo="ATR混合策略平多-超长上影线")
                    return
                if df.iloc[-1]["side"] == df.iloc[-2]["side"] == 2:  # 两根反转HA
                    self.close_position(memo="ATR混合策略平多-两根反转HA")
                    return
            else:
                if cur_ha["side"] == 2 and cur_ha["ha_close"] - cur_ha["ha_low"] > 2 * (cur_ha["ha_high"] - cur_ha["ha_close"]):  # 超长下影线
                    self.close_position(memo="ATR混合策略平空-超长下影线")
                    return
                if df.iloc[-1]["side"] == df.iloc[-2]["side"] == 1:  # 两根反转HA
                    self.close_position(memo="ATR混合策略平空-两根反转HA")
                    return
    def trend_check_stochastics(self, df, side):
        """
        stochastics check趋势信号
        :return:
        """
        if len(df) < 3:
            return None
        # if abs(df.iloc[-1]["%K"] - df.iloc[-3]["%K"]) < abs(df.iloc[-1]["%D_smooth"] - df.iloc[-3]["%D_smooth"]):
        #     return None
        if side == PositionSide.LONG:
            if df.iloc[-1]["%D_smooth"] > df.iloc[-2]["%D_smooth"]:
                return side
        if side == PositionSide.SHORT:
            if df.iloc[-1]["%D_smooth"] < df.iloc[-2]["%D_smooth"]:
                return side

    def trend_from_heikin_ashi(self, df):
        """
        从Heikin-Ashi判断趋势信号
        :return:
        """
        if len(df) < 4:
            return None
        side = None
        # 出现三根相同颜色K线
        if df.iloc[-1]["side"] == df.iloc[-2]["side"] == df.iloc[-3]["side"] and df.iloc[-3]["side"] != df.iloc[-4]["side"]:
            side = PositionSide(df.iloc[-1]["side"])
        if side is None:
            return None

        cur_ha = df.iloc[-1]
        if side == PositionSide.LONG:
            if not df.iloc[-1]["ha_close"] > df.iloc[-2]["ha_close"] > df.iloc[-3]["ha_close"]:  # not 收盘价不断上升
                return None
            if not df.iloc[-1]["ha_high"] > df.iloc[-2]["ha_high"] > df.iloc[-3]["ha_high"]:  # not 最高价不断上升
                return None

            if df.iloc[-1]["ha_high"] - df.iloc[-2]["ha_high"] < df.iloc[-2]["ha_high"] - df.iloc[-3]["ha_high"]:  # 高点之差收缩
                return None

            if cur_ha["ha_high"] - cur_ha["ha_close"] > cur_ha["ha_close"] - cur_ha["ha_open"]:  # 上影线 大于 实体
                return None
        else:
            if not df.iloc[-1]["ha_close"] < df.iloc[-2]["ha_close"] < df.iloc[-3]["ha_close"]:  # not 收盘价不断下降
                return None
            if not df.iloc[-1]["ha_low"] < df.iloc[-2]["ha_low"] < df.iloc[-3]["ha_low"]:  # not 最低价不断上升
                return None

            if df.iloc[-2]["ha_low"] - df.iloc[-1]["ha_low"] < df.iloc[-3]["ha_low"] - df.iloc[-2]["ha_low"]:  # 低点之差收缩
                return None

            if cur_ha["ha_close"] - cur_ha["ha_low"] > cur_ha["ha_open"] - cur_ha["ha_close"]:  # 下影线 大于 实体
                return None
        return side


if __name__ == '__main__':
    # 示例K线数据
    data = {
        'Date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'],
        'Open': [100, 105, 110, 115, 120],
        'High': [120, 125, 130, 135, 140],
        'Low': [95, 100, 105, 110, 115],
        'Close': [110, 115, 120, 125, 130]
    }

    # 创建DataFrame
    kline_data = pd.DataFrame(data)
    print(pd.to_datetime(kline_data['Date'], format="%Y-%m-%d"))
