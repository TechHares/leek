#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/3/18 15:19
# @Author  : shenglin.li
# @File    : strategy_macd.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal

import pandas as pd

from leek.strategy import *
from leek.trade.trade import PositionSide


class SingleMaStrategy(BaseStrategy):
    verbose_name = "单均线策略"

    def __init__(self, ma):
        self.period = int(ma.split(",")[0])

    def __calculate_ma(self, df):
        """
        计算MACD
        """
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        all_zero_or_missing_indices = df[(df['volume'] == 0) | df['volume'].isnull()].index

        df['volume'] = df['volume'].replace(Decimal("0"), Decimal("1"), limit=None)
        df.loc[all_zero_or_missing_indices, 'volume'] = Decimal("0")

        df['ma_amount'] = df['amount'].rolling(window=self.period).mean()
        df['ma_volume'] = df['volume'].rolling(window=self.period).mean()
        df['ma'] = (df['ma_amount'] / df['ma_volume']).apply(lambda x: Decimal(x))

    def handle(self):
        if self.market_data.finish != 1:
            return
        if self.g.q is None:
            self.g.q = deque(maxlen=int(self.period * 2))

        self.g.q.append(self.market_data.__json__())
        df = pd.DataFrame(list(self.g.q))
        self.__calculate_ma(df)
        self.__handle_long(df)

    def __handle_long(self, df):
        if len(df) < self.period + 5:
            return

        if self.have_position():
            if df['ma'].iloc[-1] < df['ma'].iloc[-2]:
                self.close_position()
                return

            if df['close'].iloc[-1] < df['ma'].iloc[-1]:
                self.g.cross_ma += 1
            if df['close'].iloc[-1] > df['ma'].iloc[-1]:
                self.g.cross_ma = 0

            if self.g.cross_ma > 2:
                self.close_position()
                return
        else:  # 开仓判断
            if not df['ma'].iloc[-1] > df['ma'].iloc[-2] > df['ma'].iloc[-3] > df['ma'].iloc[-4]:
                return

            if df['ma'].iloc[-1] - df['ma'].iloc[-2] <= df['ma'].iloc[-2] - df['ma'].iloc[-3]:
                return
            if df['ma'].iloc[-2] - df['ma'].iloc[-3] <= df['ma'].iloc[-3] - df['ma'].iloc[-4]:
                return
            self.g.cross_ma = 0
            self.create_order(PositionSide.LONG)


if __name__ == '__main__':
               pass
