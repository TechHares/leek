import unittest
import pandas as pd
import numpy as np
import talib as tl
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from leek.runner.view import ViewWorkflow
from leek.t.qqe_mod import QQEMod
from leek.t.boll import BollBand
from leek.t import StochRSI, RSI

class TestQQEMod(unittest.TestCase):

    def test_handle2(self):
        """
        测试 QQEMod 类的 handle2 方法。
        """
        # 初始化工作流
        workflow = ViewWorkflow(None, "4H", "2024-02-08 00:30", "2025-01-07 23:30", "ETH-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-10-15 00:30", "2024-10-20 23:30", "ETH-USDT-SWAP")

        # 初始化指标
        qqe_mod, boll, rsi = self._initialize_indicators()

        # 获取数据
        data = workflow.get_data("ETH-USDT-SWAP")

        # 更新指标并处理数据
        data = self._update_indicators(data, qqe_mod, boll, rsi)

        # 将数据转换为 DataFrame
        df = self._create_dataframe(data)

        # 绘制图表
        self._plot_data(df)

    def _initialize_indicators(self):
        """
        初始化所有技术指标。

        :return: 初始化后的指标对象
        """
        qqe_mod = QQEMod()
        boll = BollBand()
        rsi = StochRSI(14, 14, 3, 3)
        return qqe_mod, boll, rsi

    def _update_indicators(self, data, qqe_mod, boll, rsi):
        """
        更新所有技术指标。

        :param data: 输入数据
        :param qqe_mod: QQEMod 对象
        :param boll: BollBand 对象
        :param rsi: StochRSI 对象
        :return: 更新后的数据
        """
        green_color = 'green'
        red_color = 'red'
        grey_color = 'grey'

        for d in data:
            qqeMode = qqe_mod.update(d)
            if qqeMode:
                d.qqeLine, d.histo = qqeMode.qqeLine, qqeMode.histo
                d.color = green_color if qqeMode.greenBar else red_color if qqeMode.redBar else grey_color

            bo = boll.update(d)
            if bo:
                d.lower_band, d.mid, d.upper_band = bo

            r = rsi.update(d)
            if r:
                d.k, d.d = r

        return data

    def _create_dataframe(self, data):
        """
        将数据转换为 DataFrame 并添加时间戳。

        :param data: 输入数据
        :return: 转换后的 DataFrame
        """
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        return df

    def _plot_data(self, df):
        """
        绘制数据图表。

        :param df: 输入 DataFrame
        """
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

        workflow = ViewWorkflow(None, "4H", "2024-02-08 00:30", "2025-01-07 23:30", "ETH-USDT-SWAP")
        workflow.draw(fig=fig, df=df)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['upper_band'], mode='lines', name='up'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['mid'], mode='lines', name='mid'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['lower_band'], mode='lines', name='low'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['qqeLine'], mode='lines', name='qqe_line'), row=2, col=1)
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['histo'], marker={"color": df['color']}, name='histo'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['k'], mode='lines', line=dict(color='black', width=1), name='k'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['d'], mode='lines', line=dict(color='orange', width=1), name='d'), row=3, col=1)

        fig.update_layout(barmode='relative')

        print(len(df))
        fig.show()