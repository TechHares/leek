from collections import deque
from decimal import Decimal

import numpy as np
import pandas as pd
import talib as tl

from leek.t import RSI, BollBand, SPECIAL_EMA, SPECIAL_ATR, SPECIAL_BAND
from leek.t.t import T


class QQE:
    def __init__(self):
        self.qqeLine = 0.0
        self.histo = 0.0
        self.greenBar = False
        self.redBar = False


class QQEMod(T):

    def __init__(self, window=14,
                 period1=6, SF1=5, QQE1=3, threshold1=3,
                 period2=6, SF2=5, QQE2=1.61, threshold2=3,
                 max_cache=100):
        T.__init__(self, max_cache)
        self.window = window

        self.period1 = period1
        self.SF1 = Decimal(SF1)
        self.QQE1 = float(QQE1)
        self.threshold1 = Decimal(threshold1)
        self.period2 = period2
        self.SF2 = Decimal(SF2)
        self.QQE2 = float(QQE2)
        self.threshold2 = Decimal(threshold2)

        # Common constant in calculations `50 MA bollinger band`
        self.CONST50 = 50
        self.mult = float(0.35)
        self.length = self.CONST50

        self.period = max(self.period1, self.period2)
        self.q = deque(maxlen=window - 1)

        self.wilder_period = 2 * (max(period1, period2)) - 1
        self._initialize_indicators(
            {'period': period1, 'SF': SF1, 'wilder_period': self.wilder_period, 'window': window, 'attr_postfix': '1'}
        )

        self._initialize_indicators(
            {'period': period2, 'SF': SF2, 'wilder_period': self.wilder_period, 'window': window, 'attr_postfix': '2'}
        )

    def _initialize_indicators(self, params):
        period = params['period']
        SF = params['SF']  # 这个值可能用于后续计算，但不一定直接用于初始化
        wilder_period = params['wilder_period']
        attr_postfix = params['attr_postfix']  # 用于动态设置属性的前缀
        window = params['window']

        # 初始化RSI
        rsi_attr_name = f"rsi{attr_postfix}"
        setattr(self, rsi_attr_name, RSI(period))

        # 初始化EMA
        ema_attr_name = f"ema_rsi{attr_postfix}"
        setattr(self, ema_attr_name, SPECIAL_EMA(period))

        # 初始化ATR
        atr_attr_name = f"atr_rsi{attr_postfix}"
        setattr(self, atr_attr_name, SPECIAL_ATR(SF))

        # 初始化EMA_ATR
        atr_attr_name = f"ema_atr_rsi{attr_postfix}"
        setattr(self, atr_attr_name, SPECIAL_EMA(wilder_period))

        # 初始化EMA_DAR
        atr_attr_name = f"ema_dar{attr_postfix}"
        setattr(self, atr_attr_name, SPECIAL_EMA(wilder_period))

        # 初始化SPECIAL_BAND
        atr_attr_name = f"special_band{attr_postfix}"
        setattr(self, atr_attr_name, SPECIAL_BAND(window))

        atr_attr_name = f"ema_fastAtrRsiTL{attr_postfix}"
        setattr(self, atr_attr_name, SPECIAL_EMA(self.CONST50))

    def update(self, data):

        qqeMode = QQE()
        try:
            rsi = self.rsi1.update(data)
            if rsi is None:
                return qqeMode

            last = self.rsi1.last(self.period)
            if len(last) < self.period:
                return qqeMode

            emaRsi1 = self.ema_rsi1.update(rsi)
            emaRsi2 = self.ema_rsi2.update(rsi)
            lastEmaRsi1 = self.ema_rsi1.last(self.wilder_period)
            if len(lastEmaRsi1) < self.wilder_period:
                return qqeMode
            lastEmaRsi2 = self.ema_rsi2.last(self.wilder_period)
            if len(lastEmaRsi2) < self.wilder_period:
                return qqeMode
            emaLastRsi1 = lastEmaRsi1[-2]
            emaLastRsi2 = lastEmaRsi2[-2]

            atr1 = abs(emaLastRsi1 - emaRsi1)
            atr2 = abs(emaLastRsi2 - emaRsi2)
            atr_ema1 = self.ema_atr_rsi1.update(atr1)
            atr_ema2 = self.ema_atr_rsi2.update(atr2)
            dar1 = self.ema_dar1.update(atr_ema1) * self.QQE1
            dar2 = self.ema_dar2.update(atr_ema2) * self.QQE2

            lastdar1 = self.ema_dar1.last(self.period1)
            if len(lastdar1) < self.period1:
                return qqeMode

            lastdar2 = self.ema_dar2.last(self.period1)
            if len(lastdar2) < self.period2:
                return qqeMode

            band1 = self.special_band1.update(emaRsi1, dar1)
            band2 = self.special_band2.update(emaRsi2, dar2)
            upper, lower = self.bollinger_uplower(band1)

            qqeline = band2.fastAtrRsiTL - self.CONST50
            histo = band2.rsiMa - self.CONST50

            greenbar1 = band2.rsiMa - self.CONST50 > self.threshold2
            greenbar2 = band1.rsiMa - 50 > upper

            redbar1 = band2.rsiMa - self.CONST50 < 0 - self.threshold2
            redbar2 = band1.rsiMa - self.CONST50 < lower

            qqeMode.qqeLine = qqeline
            qqeMode.histo = histo
            qqeMode.greenBar = greenbar1 and greenbar2
            qqeMode.redBar = redbar1 and redbar2
            return qqeMode

        finally:
            if data.finish == 1:
                self.q.append(qqeMode)
                self.cache.append(qqeMode)

    def bollinger_uplower(self, band):
        basis = self.ema_fastAtrRsiTL1.update(band.fastAtrRsiTL - self.CONST50)

        lastBand1 = self.special_band1.last(self.CONST50)
        lastFastAtrRsiTL_values = [obj.fastAtrRsiTL - self.CONST50 for obj in lastBand1]
        dev = self.mult * np.std(lastFastAtrRsiTL_values)

        upper = basis + dev
        lower = basis - dev
        return upper, lower
