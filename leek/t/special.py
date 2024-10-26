import math
from collections import deque
from decimal import Decimal

import numpy as np
import pandas as pd

from leek.common import G
from leek.t.t import T


class SPECIAL_EMA(T):
    """
    加权平均
    """

    def __init__(self, window=9, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.pre_ma = None
        self.alpha = float(2 / (self.window + 1))

    def update(self, data: float):
        ma = None
        try:
            if self.pre_ma is None:
                ma = data
                return ma
            ma = self.alpha * data + (1 - self.alpha) * self.pre_ma
            return ma
        finally:
            self.pre_ma = ma
            self.cache.append(ma)


class SPECIAL_ATR(T):
    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, data: float):
        tr = 0.0
        atr = 0.0
        try:
            ls = list(self.q)
            if len(ls) > 0:
                tr = self.last(1)[0] - data
                atr = (sum([d.tr for d in ls]) + tr) / (len(ls) + 1)
            return atr
        finally:
            self.q.append(G(tr=tr, atr=atr))
            self.cache.append(atr)


class QQEBand:
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
    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.q = deque(maxlen=window - 1)

    def update(self, rsiMa, dar):
        band = QQEBand()

        try:
            if len(self.q) < 3:
                return band

            newShortBand = rsiMa + dar
            newLongBand = rsiMa - dar
            longBand = 0.0
            shortBand = 0.0
            lastBand = self.q[-1]

            if lastBand.rsiMa > lastBand.longBand and rsiMa > lastBand.longBand:
                longBand = max(lastBand.longBand, newLongBand)
            else:
                longBand = newLongBand

            if lastBand.rsiMa < lastBand.shortBand and rsiMa < lastBand.shortBand:
                shortBand = min(lastBand.shortBand, newShortBand)
            else:
                shortBand = newShortBand

            lastLongBand = self.q[-1].longBand
            lastShortBand = self.q[-1].shortBand
            lastRsiMa = self.q[-1].rsiMa

            longBandMinus2 = self.q[-2].longBand
            shortBandMinu2 = self.q[-2].shortBand

            crossAbove1 = (longBandMinus2 < lastRsiMa) & (lastLongBand >= rsiMa)
            crossBelow1 = (longBandMinus2 > lastRsiMa) & (lastLongBand <= rsiMa)
            crosses1 = crossAbove1 | crossBelow1

            crossAbove2 = (lastRsiMa < shortBandMinu2) & (rsiMa >= lastShortBand)
            crossBelow2 = (lastRsiMa > shortBandMinu2) & (rsiMa <= lastShortBand)
            crosses2 = crossAbove2 | crossBelow2

            trend = (
                1
                if crosses2
                else -1
                if crosses1
                else 1
            )

            fastAtrRsiTL = (longBand if trend == 1 else shortBand)

            band.newLongBand = newLongBand
            band.newShortBand = newShortBand
            band.longBand = longBand
            band.shortBand = shortBand
            band.rsiMa = rsiMa
            band.dar = dar
            band.fastAtrRsiTL = fastAtrRsiTL
            return band

        finally:
            self.q.append(band)
            self.cache.append(band)
