

from leek.t.t import T
from leek.common.utils import *
from leek.t import MA,ATR

class KeltnerBand(T):

    def __init__(self, window=20, num_std_dev=2, max_cache=100):
        T.__init__(self, max_cache)
        self.window = window
        self.num_std_dev = Decimal(num_std_dev)
        self.q = deque(maxlen=window - 1)
        self.ma = MA(window)
        self.atr = ATR(window)

    def update(self, data):
        keltner_band = None
        try:
            middle = self.ma.update(data)
            if not middle:
                return keltner_band

            ls = list(self.q)
            ls.append(data.close)
            atr = self.atr.update(data)
            upper_band = middle + (atr * self.num_std_dev)
            lower_band = middle - (atr * self.num_std_dev)
            keltner_band = (lower_band, middle, upper_band)
            return keltner_band
        finally:
            if data.finish == 1:
                self.q.append(data.close)
                self.cache.append(keltner_band)





