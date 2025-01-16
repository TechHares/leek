from leek.t.t import T
from leek.common.utils import *
from leek.t import MA,ATR

class SuperTrend(T):

    def __init__(self, num_atr=3, window=10, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.num_atr = Decimal(num_atr)
        self.q = deque(maxlen=window - 1)
        self.atr = ATR(window)

    def update(self, data):
        super_trend = None
        try:
            ls = list(self.q)
            ls.append(data.close)
            atr = self.atr.update(data)
            price = (data.high+data.low)/2
            upper_band = price + (atr * self.num_atr)
            lower_band = price - (atr * self.num_atr)
            super_trend = (lower_band,  upper_band)
            return super_trend
        finally:
            if data.finish == 1:
                self.q.append(data.close)
                self.cache.append(super_trend)