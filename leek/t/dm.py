#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/18 20:24
# @Author  : shenglin.li
# @File    : dm.py
# @Software: PyCharm
from leek.t.atr import TR, ATR
from leek.t.ma import EMA, MA
from leek.t.t import T


class DMI(T):
    """
    趋向指标(DMI)实际上是由三个独立的指标组合成一个的集合。方向变动由平均趋向指标(ADX)、正趋向指标(+DI)和负趋向指标(-DI)组成。
    DMI的目的是确定是否存在趋势。它根本不考虑方向。其他两个指标(+DI和-DI)用于补充ADX。它们的作用是确定趋势方向。
    通过将这三者结合起来，技术分析员就有了一种方法来确定和测量趋势的强度和方向。

    要分析趋势强度，重点应放在ADX线上，而不是+DI或-DI线上。怀尔德（Wilder）认为DMI读数高于25表示趋势强劲，而读数低于20则表示趋势弱或不存在。
    上述两个值是不确定的。但是，如前所述，有经验的交易者不会采用25和20的值且不会将其应用于每种情况。真正的强势或弱势取决于所交易的商品。历史走势分析可以帮助确定适当的值。
    """

    def __init__(self, adx_smoothing=6, di_length=14, max_cache=100):
        T.__init__(self, max(max_cache, adx_smoothing))
        self.adx_smoothing = adx_smoothing
        self.di_length = di_length

        self.tr_cal = TR(di_length)
        self.up_di_smooth = MA(di_length, vfunc=lambda x: x)
        self.down_di_smooth = MA(di_length, vfunc=lambda x: x)
        self.dx_smooth = EMA(adx_smoothing, vfunc=lambda x: x)
        self.pre = None

    def update(self, data):
        d = None
        try:
            if self.pre is None:
                return None, None, None, None
            tr = self.tr_cal.update(data)
            up_dm = max(data.high - self.pre.high, 0)
            up_di = self.up_di_smooth.update((100 * up_dm / tr) if tr != 0 else 100, data.finish == 1)
            down_dm = max(self.pre.low - data.low, 0)
            down_di = self.down_di_smooth.update((100 * down_dm / tr) if tr != 0 else 100, data.finish == 1)
            if up_di is None or down_di is None:
                return None, None, None, None

            dx = (abs(up_di - down_di) / (up_di + down_di) * 100) if up_di + down_di > 0 else 100
            adx = self.dx_smooth.update(dx, data.finish == 1)
            last = self.last(self.adx_smoothing)
            adxr = adx
            if len(last) == self.adx_smoothing:
                adxr = (adxr + last[0][0]) / 2
            d = (adx, up_di, down_di, adxr)
            return adx, up_di, down_di, adxr
        finally:
            if data.finish == 1:
                self.pre = data
                if d:
                    self.cache.append(d)


if __name__ == '__main__':
    pass
