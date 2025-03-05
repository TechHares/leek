#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/8 22:40
# @Author  : shenglin.li
# @File    : strategy_chan1_test.py
# @Software: PyCharm
import decimal
import unittest

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go

from leek.common import EventBus
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_chan import ChanStrategy
from leek.strategy.strategy_chan1 import ChanV2Strategy
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.trade.trade import PositionSide


class TestChan1(unittest.TestCase):
    def test_handle(self):
        self.strategy = ChanV2Strategy()
        PositionRateManager.__init__(self.strategy, 1)
        PositionDirectionManager.__init__(self.strategy, 4)
        JustFinishKData.__init__(self.strategy, False)

        self.bus = EventBus()
        # workflow = ViewWorkflow(self.strategy, "5m", "2024-06-28", "2024-07-01", "AEVO-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "5m", "2024-07-14", "2024-07-25", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(self.strategy, "5m", "2024-12-15 23:10", "2025-01-07 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(self.strategy, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")

        workflow.start()
        """
        只是在形态学中，由于没有背驰的概念， 所以第一买卖点是抓不住了，但第二买卖点是肯定没问题的。
        单纯用形态学去操作，就是任何对最后一个中枢的回拉后第一个与回拉反向的不创新高或新低的中枢同级别离开，就是买卖段
        
        当然，上面只是说如果只用形态学，也可以进行操作，但实际上，当然是动力学、形态学一起用更有效。所以，千万别认为以后就只用形态学了。
        不过这里有一个用处，就是那些对背驰、区间套没什么信心的，可以先多从形态学着手。而且，形态分析不好，也动力不起来。
        
        分型-笔-线段-最小级别中枢-各级别中枢、走势类型
        """


        for bi in self.strategy.bi_manager:
            bi.mark_on_data()
            # for ck in bi.chan_k_list:
            #     ck.mark_on_data()

        for seg in self.strategy.seg_manager:
            seg.mark_on_data()

        df = pd.DataFrame([x.__json__() for x in workflow.kline_data_g])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=1, col=1)

        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        for level in self.strategy.zs_manager.zs_dict:
            for zs in self.strategy.zs_manager.zs_dict[level]:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[level - 1], width=zs.level),
                    fillcolor=None,
                    name='Highlight Area'
                )

        if "seg" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                           name='segment', connectgaps=True), row=1, col=1)


        # df["benchmark"] = df["close"] / df.iloc[1]["close"]
        # df["profit"] = df["balance"] / decimal.Decimal("1000")
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['benchmark'], mode='lines', name='benchmark'), row=2, col=1)
        # fig.add_trace(go.Scatter(x=df['Datetime'], y=df['profit'], mode='lines', name='profit'), row=2, col=1)
        fig.update_layout(height=500)
        workflow.draw(fig=fig, df=df)
        fig.show()


if __name__ == '__main__':
    unittest.main()
