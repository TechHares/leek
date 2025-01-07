import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.runner.view import ViewWorkflow
from leek.t.super_trend import SuperTrend

class TestSuperTrend(unittest.TestCase):
        def test_handle1(self):
            workflow = ViewWorkflow(None, "5m", "2024-09-01 14:30", "2024-09-18 18:30", "ETH-USDT-SWAP")
            super_trend = SuperTrend()
            data = workflow.get_data("ETH-USDT-SWAP")
            for d in data:
                trend = super_trend.update(d)
                if trend:
                    d.upper_band, d.lower_band = trend
            df = pd.DataFrame([x.__json__() for x in data])
            df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['upper_band'], mode='lines', name='up'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['lower_band'], mode='lines', name='low'), row=1, col=1)

            workflow.draw(fig=fig, df=df)
            print(len(df))
            fig.show()