import unittest

import pandas as pd
import numpy as np
import talib as tl
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t.qqe_mod import QQEMod
from leek.t.super_trend import SuperTrend
from leek.t.boll import BollBand
from leek.t import StochRSI, RSI

class TestQQEMod(unittest.TestCase):

    def test_handle2(self):
        workflow = ViewWorkflow(None, "4H", "2024-02-08 00:30", "2024-11-03 23:30", "ETH-USDT-SWAP")
        #workflow = ViewWorkflow(None, "5m", "2024-10-15 00:30", "2024-10-20 23:30", "ETH-USDT-SWAP")
        qqe_mod = QQEMod()
        #super_trend = SuperTrend()
        boll = BollBand()
        rsi = StochRSI(14, 14, 3, 3)
        data = workflow.get_data("ETH-USDT-SWAP")

        green_color = 'green'
        red_color = 'red'
        grey_color = 'grey'
        for d in data:
            qqeMode = qqe_mod.update(d)
            if qqeMode:
                d.qqeLine, d.histo = qqeMode.qqeLine, qqeMode.histo
                if qqeMode.greenBar:
                    d.color = green_color
                elif qqeMode.redBar:
                    d.color = red_color
                else:
                    d.color = grey_color
            # trend = super_trend.update(d)
            # if trend:
            #     d.upper_band, d.lower_band = trend
            bo = boll.update(d)
            if bo:
                d.lower_band, d.mid, d.upper_band = bo
            r = rsi.update(d)
            if r:
                d.k, d.d = r

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        workflow.draw(fig=fig, df=df)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['upper_band'], mode='lines', name='up'), row=1, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['lower_band'], mode='lines', name='low'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['upper_band'], mode='lines', name='up'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['mid'], mode='lines', name='mid'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['lower_band'], mode='lines', name='low'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['qqeLine'], mode='lines', name='qqe_line'), row=2, col=1)
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['histo'], marker={"color": df['color']}, name='histo'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines',
                                 line=dict(color='black', width=1), name='k'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines',
                                 line=dict(color='orange', width=1), name=''), row=3, col=1)
        fig.update_layout(
            barmode='relative'
        )
        print(len(df))
        fig.show()

    def test_handle1(self):
        workflow = ViewWorkflow(None, "5m", "2024-09-01 14:30", "2024-09-18 18:30", "ETH-USDT-SWAP")
        qqe_mod = QQEMod()
        data = workflow.get_data("ETH-USDT-SWAP")
        df = pd.DataFrame([x.__json__() for x in data])
        src: pd.Series = df["close"]

        # Common constant in calculations `50 MA bollinger band`
        CONST50 = 50

        # First RSI input block
        RSI_Period: int = 6
        SF: int = 5
        QQE: float = 3.0
        ThreshHold: int = 3  # !not used input var

        # Second RSI input block
        RSI_Period2: int = 6
        SF2: int = 5
        QQE2: float = 1.61
        ThreshHold2: int = 3

        src2: pd.Series = df["close"]

        # Bollinger input block
        length: int = CONST50
        mult: float = 0.35

        FastAtrRsiTL, RsiMa = self.qqe_hist(src, RSI_Period, SF, QQE)
        FastAtrRsi2TL, RsiMa2 = self.qqe_hist(src2, RSI_Period2, SF2, QQE2)

        qqe_line = FastAtrRsi2TL - CONST50
        histo2 = RsiMa2 - CONST50

        upper, lower = self.bollinger_uplower(FastAtrRsiTL, length, mult, CONST50)

        qqe_up, qqe_down = self.qqe_up_down(RsiMa, RsiMa2, upper, lower, ThreshHold2, CONST50)

        test = None


    # --------------------------FUNCIONS------------------------------
    def cross(self, x: pd.Series, y: pd.Series) -> pd.Series:
        """
        Returns a boolean Series indicating where two pandas Series have crossed.
        """
        # Ensure the inputs are pandas Series
        x = pd.Series(x)
        y = pd.Series(y)

        # Compare the values at corresponding indices
        cross_above = (x.shift(1) < y.shift(1)) & (x >= y)
        cross_below = (x.shift(1) > y.shift(1)) & (x <= y)

        # Combine the above and below crosses into a single boolean Series
        crosses = cross_above | cross_below

        return crosses

    def qqe_hist(self, src: pd.Series, RSI_Period: int, SF: int, QQE: float) -> tuple:
        Wilders_Period: int = RSI_Period * 2 - 1
        Rsi = tl.RSI(src, RSI_Period)
        RsiMa = tl.EMA(Rsi, SF)
        AtrRsi = np.abs(np.roll(RsiMa.copy(), 1) - RsiMa)
        MaAtrRsi = tl.EMA(AtrRsi, Wilders_Period)
        dar = tl.EMA(MaAtrRsi, Wilders_Period) * QQE

        longband: pd.Series = np.zeros_like(src, dtype=float)
        shortband: pd.Series = np.zeros_like(src, dtype=float)
        trend: pd.Series = np.zeros_like(src, dtype=int)
        FastAtrRsiTL: pd.Series = np.zeros_like(src, dtype=float)

        DeltaFastAtrRsi = dar
        RSIndex = RsiMa
        newshortband = RSIndex + DeltaFastAtrRsi
        newlongband = RSIndex - DeltaFastAtrRsi

        for i in range(1, len(src)):
            if RSIndex[i - 1] > longband[i - 1] and RSIndex[i] > longband[i - 1]:
                longband[i] = max(longband[i - 1], newlongband[i])
            else:
                longband[i] = newlongband[i]

            if RSIndex[i - 1] < shortband[i - 1] and RSIndex[i] < shortband[i - 1]:
                shortband[i] = min(shortband[i - 1], newshortband[i])
            else:
                shortband[i] = newshortband[i]

        cross_1 = self.cross(np.roll(longband.copy(), 1), RSIndex)
        cross_2 = self.cross(RSIndex, np.roll(shortband.copy(), 1))

        for i in range(1, len(src)):
            trend[i] = (
                1
                if cross_2[i]
                else -1
                if cross_1[i]
                else 1
                if np.isnan(trend[i - 1])
                else trend[i - 1]
            )

        FastAtrRsiTL = np.where(trend == 1, longband, shortband)

        FastAtrRsiTL = np.nan_to_num(FastAtrRsiTL)

        return FastAtrRsiTL, RsiMa

    def bollinger_uplower(self,
            FastAtrRsiTL: np.ndarray, length: int, mult: float, CONST50: int
    ) -> tuple:
        basis = tl.SMA(FastAtrRsiTL - CONST50, timeperiod=length)
        dev = mult * tl.STDDEV(FastAtrRsiTL - CONST50, length)

        upper = basis + dev
        lower = basis - dev
        return upper, lower

    def zero_cross(self, src: pd.Series, RSIndex: np.ndarray, CONST50: int) -> tuple:
        QQEzlong: np.ndarray = np.zeros_like(src, dtype=int)
        QQEzshort: np.ndarray = np.zeros_like(src, dtype=int)

        for i in range(1, len(src)):
            QQEzlong[i] = QQEzlong[i - 1]
            QQEzshort[i] = QQEzshort[i - 1]

            QQEzlong[i] = QQEzlong[i] + 1 if RSIndex[i] >= CONST50 else 0
            QQEzshort[i] = QQEzshort[i] + 1 if RSIndex[i] < CONST50 else 0
        return QQEzlong, QQEzshort

    def qqe_up_down(self, RsiMa, RsiMa2, upper, lower, ThreshHold2, CONST50) -> tuple:
        Greenbar1: np.ndarray = RsiMa2 - CONST50 > ThreshHold2
        Greenbar2: np.ndarray = RsiMa - CONST50 > upper

        Redbar1: np.ndarray = RsiMa2 - CONST50 < 0 - ThreshHold2
        Redbar2: np.ndarray = RsiMa - CONST50 < lower

        qqe_up_cond = Greenbar1 & Greenbar2
        qqe_down_cond = Redbar1 & Redbar2

        qqe_up = np.full_like(RsiMa2, fill_value=np.nan)
        qqe_down = np.full_like(RsiMa2, fill_value=np.nan)

        qqe_up = np.where(qqe_up_cond, RsiMa2 - CONST50, np.nan)
        qqe_down = np.where(qqe_down_cond, RsiMa2 - CONST50, np.nan)

        return qqe_up, qqe_down
