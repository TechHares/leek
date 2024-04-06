#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/3/18 15:19
# @Author  : shenglin.li
# @File    : strategy_macd.py
# @Software: PyCharm
import datetime
from collections import deque
from decimal import Decimal

import pandas as pd

from leek.common import G
from leek.strategy import *
from leek.strategy.common import *
from leek.trade.trade import PositionSide


class MacdStrategy(BaseStrategy):
    verbose_name = "MACD策略"

    def __init__(self, ma, smoothing_period, max_single_position):
        # macd
        # self.fast_line_period = 5
        # self.slow_line_period = 17
        # self.long_line_period = 34
        # self.average_moving_period = 7
        self.fast_line_period = int(ma.split(",")[0])
        self.slow_line_period = int(ma.split(",")[1])
        self.long_line_period = int(ma.split(",")[2])
        self.average_moving_period = int(smoothing_period.split(",")[0])

        self.max_single_position = Decimal(max_single_position)

    def __calculate_macd(self, df):
        """
        计算MACD
        """
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        all_zero_or_missing_indices = df[(df['volume'] == 0) | df['volume'].isnull()].index

        df['volume'] = df['volume'].replace(Decimal("0"), Decimal("1"), limit=None)
        df['avg_price'] = df['amount'] / df['volume']
        df.loc[all_zero_or_missing_indices, 'volume'] = Decimal("0")

        df['ma_fast'] = df['avg_price'].rolling(window=self.fast_line_period).mean().apply(lambda x: Decimal(x))
        df['ma_slow'] = df['avg_price'].rolling(window=self.slow_line_period).mean().apply(lambda x: Decimal(x))
        df['ma_long'] = df['avg_price'].rolling(window=self.long_line_period).mean().apply(lambda x: Decimal(x))

        df['dif'] = df['ma_fast'] - df['ma_slow']
        df['dea'] = df['dif'].ewm(span=self.average_moving_period, adjust=False).mean().apply(lambda x: Decimal(x))
        df['m'] = df['dif'] - df['dea']

    def handle(self):
        if self.market_data.finish != 1:
            return
        if self.g.q is None:
            self.g.q = deque(maxlen=int(self.long_line_period * 2))

        self.g.q.append(self.market_data.__json__())
        df = pd.DataFrame(list(self.g.q))
        self.__calculate_macd(df)
        self.__handle_long(df)

    def __handle_long(self, df):
        if len(df) < self.long_line_period + 5:
            return

        if self.have_position():
            # if df['dif'].iloc[-1] < 0 or df['m'].iloc[-1] < 0:  # dead cross or under zeroline
            #     self.close_position()
            #     return
            # if df['close'].iloc[-1] < df['ma_slow'].iloc[-1] or df['close'].iloc[-1] < df['ma_long'].iloc[-1]:  # cross slow/long line
            #     self.close_position()
            #     return
            if self.g.cross_fast_line is None and df['close'].iloc[-1] < df['ma_long'].iloc[-1]:
                self.g.cross_fast_line = True
                return
            if self.g.cross_fast_line is not None and df['close'].iloc[-1] < df['ma_long'].iloc[-1]:
                self.close_position()
                return
        else:  # 开仓判断
            if len(df['dif']) < 4 or not df['dif'].iloc[-1] > df['dif'].iloc[-2] > df['dif'].iloc[-3]:
                return
            if not df['dea'].iloc[-1] > df['dea'].iloc[-2] > df['dea'].iloc[-3]:
                return
            if df['ma_fast'].iloc[-1] + df['ma_fast'].iloc[-3] < 2 * df['ma_fast'].iloc[-2]:
                return

            if not df['ma_long'].iloc[-1] > df['ma_long'].iloc[-2] > df['ma_long'].iloc[-3]:
                return
            if not df['ma_fast'].iloc[-1] > df['ma_fast'].iloc[-2] > df['ma_fast'].iloc[-3]:
                return
            if not df['ma_slow'].iloc[-1] > df['ma_slow'].iloc[-2] > df['ma_slow'].iloc[-3]:
                return

            if df['dif'].iloc[-1] < 0 or df['m'].iloc[-1] < 0:
                return

            if df['m'].iloc[-1] > 0 and df['m'].iloc[-2] > 0 and df['m'].iloc[-3] > 0 and df['m'].iloc[-4] > 0:  # gold cross more 4 kline
                return

            if df['m'].iloc[-1] < df['m'].iloc[-2]:  # 趋势减缓
                return

            gold_cross = df[df['m'] < 0]
            if len(gold_cross) < 1:
                return
            cross_point = gold_cross.iloc[-1]
            dt_rate = (df['close'].iloc[-1] - cross_point['close']) / cross_point['close']
            dt_rate2 = (df['ma_long'].iloc[-1] - cross_point['close']) / cross_point['close']
            if dt_rate < 0 or dt_rate > Decimal("0.03") or dt_rate2 > Decimal("0.01"):
                return
            self.create_order(PositionSide.LONG)

    def close_position(self, memo="", extend=None):
        win = super().close_position()
        risk_context = self.g.risk_context
        risk_context.res.append(win)
        r = list(risk_context.res)
        if r[-1]:  # 盈利
            risk_context.amplify = len([x for x in r if x]) / Decimal(10) + 1
            risk_context.risk_level = 0
            return

        if len(r) > 3 and not r[-2] and not r[-3]:  # 3次连续失败
            if len(r) > 4 and not r[-4]:  # 4次连续失败
                if len(r) > 5 and not r[-5]:  # 5次连续失败
                    risk_context.amplify = Decimal("0.2")
                    return
                risk_context.amplify = Decimal("0.5")
                return
            risk_context.amplify = Decimal("0.8")
            return

    def create_order(self, side: PositionSide, position_rate="0.5", memo="", extend=None):
        if self.g.risk_context is None:
            self.g.risk_context = G(res=deque(maxlen=10), amplify=Decimal("1"))
        risk_context = self.g.risk_context
        super().create_order(side, Decimal(self.max_single_position) * risk_context.amplify, memo, extend)


if __name__ == '__main__':
    pass
