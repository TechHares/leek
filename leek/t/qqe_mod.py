from collections import deque
from decimal import Decimal

import numpy as np
import pandas as pd
import talib as tl

from leek.t import RSI, BollBand, SPECIAL_EMA, SPECIAL_ATR, SPECIAL_BAND
from leek.t.t import T


class QQE:
    """
       QQE (Quantitative Qualitative Estimation) 指标类，用于存储QQE指标的结果。
       QQE MOD指标在设计中综合了多种市场因素，如价格波动、趋势强度等，为投资者提供了全面的市场分析视角。
       一、红绿灰柱的解读
        绿柱：当QQE MOD指标显示绿柱时，这通常意味着市场处于上涨趋势中，或者上涨动能正在增强。绿柱的高度和持续时间可以反映上涨趋势的力度和可持续性。在强势市场中，绿柱可能会连续出现，并伴随着股价的不断上涨。
        红柱：与绿柱相反，红柱的出现通常表示市场处于下跌趋势中，或者下跌动能正在增强。红柱的高度和持续时间同样可以反映下跌趋势的力度和可持续性。在弱势市场中，红柱可能会连续出现，并伴随着股价的不断下跌。
        灰柱：灰柱的出现则可能表示市场处于相对平衡的状态，或者上涨和下跌动能相互抵消。这种状态下，市场的方向可能不太明确，投资者需要更加谨慎地观察和分析。
        二、使用场景
        趋势判断：通过观察QQE MOD红绿灰柱的变化，投资者可以更加直观地判断市场的趋势。例如，当红柱连续出现时，可能意味着市场处于上涨趋势中；而当绿柱连续出现时，则可能表示市场处于下跌趋势中。这有助于投资者更好地把握市场的整体方向。
        交易决策：在交易过程中，QQE MOD红绿灰柱的变化也可以为投资者提供明确的买入和卖出信号。例如，当市场从绿柱转为红柱时，可能是一个买入的时机；而当市场从红柱转为绿柱时，则可能是一个卖出的时机。当然，投资者还需要结合其他技术指标和市场信息来做出最终的交易决策。
        风险管理：QQE MOD红绿灰柱还可以用于风险管理。例如，当市场出现连续的绿柱时，投资者可能需要更加警惕市场的下跌风险，并考虑适当减少仓位或设置止损点来规避潜在损失。同样地，当市场出现连续的红柱时，投资者也需要关注市场的过热风险，并考虑适当降低仓位或锁定利润。
    """
    def __init__(self):
        self.qqeLine = 0.0
        self.histo = 0.0
        self.greenBar = False
        self.redBar = False


class QQEMod(T):
    """
       QQE 指标计算类，继承自 T 类。
    """
    def __init__(self, window=14,
                 period1=6, SF1=5, QQE1=3, threshold1=3,
                 period2=6, SF2=5, QQE2=1.61, threshold2=3,
                 max_cache=100):
        """
            初始化 QQEMod 类。

            :param window: 窗口大小
            :param period1: 第一个周期
            :param SF1: 第一个平滑因子
            :param QQE1: 第一个QQE因子
            :param threshold1: 第一个阈值
            :param period2: 第二个周期
            :param SF2: 第二个平滑因子
            :param QQE2: 第二个QQE因子
            :param threshold2: 第二个阈值
            :param max_cache: 缓存的最大大小
        """
        super().__init__(max_cache)
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
        """
            初始化各种技术指标。

            :param params: 包含周期、平滑因子、wild期和窗口大小的参数字典
        """
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
        ema_atr_attr_name = f"ema_atr_rsi{attr_postfix}"
        setattr(self, ema_atr_attr_name, SPECIAL_EMA(wilder_period))

        # 初始化EMA_DAR
        ema_dar_attr_name = f"ema_dar{attr_postfix}"
        setattr(self, ema_dar_attr_name, SPECIAL_EMA(wilder_period))

        # 初始化SPECIAL_BAND
        special_band_attr_name = f"special_band{attr_postfix}"
        setattr(self, special_band_attr_name, SPECIAL_BAND(window))

        ema_fastAtrRsiTL_attr_name = f"ema_fastAtrRsiTL{attr_postfix}"
        setattr(self, ema_fastAtrRsiTL_attr_name, SPECIAL_EMA(self.CONST50))

    def update(self, data):
        """
            更新 QQE 指标。

            :param data: 输入数据
            :return: QQE 对象，包含 QQE 线、历史柱、绿色柱和红色柱的状态
        """
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
        """
        计算布林带的上下轨。

        :param band: 特殊带对象
        :return: 上轨和下轨的值
        """
        basis = self.ema_fastAtrRsiTL1.update(band.fastAtrRsiTL - self.CONST50)

        lastBand1 = self.special_band1.last(self.CONST50)
        lastFastAtrRsiTL_values = [obj.fastAtrRsiTL - self.CONST50 for obj in lastBand1]
        dev = self.mult * np.std(lastFastAtrRsiTL_values)

        upper = basis + dev
        lower = basis - dev
        return upper, lower
