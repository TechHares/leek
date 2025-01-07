from collections import deque
from decimal import Decimal

import numpy as np

from leek.t.t import T


class SPECIAL_EMA(T):
    """
    加权平均（指数移动平均线）
    """

    def __init__(self, window=9, max_cache=100):
        super().__init__(max_cache)
        self.window = window
        self.pre_ma = None
        self.alpha = 2 / (self.window + 1)

    def update(self, data: float) -> float:
        """
        更新指数移动平均线。

        :param data: 输入数据
        :return: 更新后的指数移动平均线值
        """
        if self.pre_ma is None:
            self.pre_ma = data
            self.cache.append(self.pre_ma)
            return self.pre_ma

        self.pre_ma = self.alpha * data + (1 - self.alpha) * self.pre_ma
        self.cache.append(self.pre_ma)
        return self.pre_ma


class SPECIAL_ATR(T):
    """
    平均真实波幅（Average True Range）
    """

    def __init__(self, window=14, max_cache=100):
        super().__init__(max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, data: float) -> float:
        """
        更新平均真实波幅。

        :param data: 输入数据
        :return: 更新后的平均真实波幅值
        """
        tr = 0.0
        atr = 0.0

        if self.q:
            tr = abs(self.last(1)[0] - data)
            atr = (sum(d.tr for d in self.q) + tr) / (len(self.q) + 1)

        self.q.append(G(tr=tr, atr=atr))
        self.cache.append(atr)
        return atr


class QQEBand:
    """
    QQE 带对象，存储各种带的值
    """

    def __init__(self, newLongBand=0.0, newShortBand=0.0,
                 longBand=0.0, shortBand=0.0,
                 rsiMa=0.0, dar=0.0,
                 fastAtrRsiTL=0.0):
        self.newLongBand = float(newLongBand)
        self.newShortBand = float(newShortBand)
        self.longBand = float(longBand)
        self.shortBand = float(shortBand)
        self.rsiMa = float(rsiMa)
        self.dar = float(dar)
        self.fastAtrRsiTL = float(fastAtrRsiTL)


class SPECIAL_BAND(T):
    """
    特殊带（SPECIAL_BAND）
    """

    def __init__(self, window=14, max_cache=100):
        super().__init__(max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, rsiMa: float, dar: float) -> QQEBand:
        """
        更新特殊带。

        :param rsiMa: RSI 移动平均线值
        :param dar: DAR 值
        :return: 更新后的 QQEBand 对象
        """
        band = QQEBand()

        if len(self.q) < 3:
            self.q.append(band)
            self.cache.append(band)
            return band

        newShortBand = rsiMa + dar
        newLongBand = rsiMa - dar
        lastBand = self.q[-1]

        longBand = max(lastBand.longBand, newLongBand) if (lastBand.rsiMa > lastBand.longBand and rsiMa > lastBand.longBand) else newLongBand
        shortBand = min(lastBand.shortBand, newShortBand) if (lastBand.rsiMa < lastBand.shortBand and rsiMa < lastBand.shortBand) else newShortBand

        lastLongBand = lastBand.longBand
        lastShortBand = lastBand.shortBand
        lastRsiMa = lastBand.rsiMa

        longBandMinus2 = self.q[-2].longBand
        shortBandMinus2 = self.q[-2].shortBand

        crossAbove1 = (longBandMinus2 < lastRsiMa) and (lastLongBand >= rsiMa)
        crossBelow1 = (longBandMinus2 > lastRsiMa) and (lastLongBand <= rsiMa)
        crosses1 = crossAbove1 or crossBelow1

        crossAbove2 = (lastRsiMa < shortBandMinus2) and (rsiMa >= lastShortBand)
        crossBelow2 = (lastRsiMa > shortBandMinus2) and (rsiMa <= lastShortBand)
        crosses2 = crossAbove2 or crossBelow2

        trend = 1 if crosses2 else (-1 if crosses1 else 1)

        fastAtrRsiTL = longBand if trend == 1 else shortBand

        band.newLongBand = newLongBand
        band.newShortBand = newShortBand
        band.longBand = longBand
        band.shortBand = shortBand
        band.rsiMa = rsiMa
        band.dar = dar
        band.fastAtrRsiTL = fastAtrRsiTL

        self.q.append(band)
        self.cache.append(band)
        return band
