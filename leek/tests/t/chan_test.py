#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/14 16:10
# @Author  : shenglin.li
# @File    : chan_test.py
# @Software: PyCharm
import decimal
import unittest
from decimal import Decimal

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly.express as px

from leek.common import EventBus
from leek.common.utils import DateTime
from leek.runner.view import ViewWorkflow
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData, DynamicRiskControl
from leek.strategy.strategy_rsi import RSIStrategy
from leek.strategy.strategy_td import TDStrategy
from leek.t import KDJ
from leek.t import *
from leek.trade.trade import PositionSide

class TestChan(unittest.TestCase):

    def test_animal_k(self):
        workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-17 20:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')



    def test_k(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 23:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-17 20:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        k = ChanKManager()
        for d in data:
            k.update(d)

        for ck in k:
            ck.mark_on_data()

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

        fig.add_trace(go.Candlestick(x=df['Datetime'],
                                     open=df['chan_open'],
                                     high=df['chan_high'],
                                     low=df['chan_low'],
                                     close=df['chan_close'],
                                     text=df["ck_idx"], name=df.iloc[0]["symbol"]), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_bi(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 23:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 23:10", "2024-07-19 10:10", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        bi_manager = ChanBIManager(bi_valid_method=BiFXValidMethod.STRICT)
        for d in data:
            bi_manager.update(d)

        for bi in bi_manager:
            bi.mark_on_data()
            for ck in bi.chan_k_list:
                ck.mark_on_data()


        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=1, col=1)

        fig.add_trace(go.Candlestick(x=df['Datetime'],
                                     open=df['chan_open'],
                                     high=df['chan_high'],
                                     low=df['chan_low'],
                                     close=df['chan_close'],
                                     name=df.iloc[0]["symbol"]), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_seg(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 16:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "1m", "2024-07-20 06:55", "2024-07-20 15:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-17 20:30", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-19 20:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        bi_manager = ChanBIManager(bi_valid_method=BiFXValidMethod.NORMAL)
        seg_manager = ChanSegmentManager()
        for d in data:
            bi_manager.update(d)
            if not bi_manager.is_empty():
                seg_manager.update(bi_manager[-1])


        for bi in bi_manager:
            bi.mark_on_data()
            for ck in bi.chan_k_list:
                ck.mark_on_data()


        for seg in seg_manager:
            seg.mark_on_data()
            print(f"线段：{seg.idx}, 笔列表：{[str(bi) + '/' + DateTime.to_date_str(bi.chan_k_list[0].klines[0].timestamp) for bi in seg.bi_list]}")

        df = pd.DataFrame([x.__json__() for x in data])
        # columns = ["timestamp","open","high","low","close"]
        # df[columns].to_csv('data.csv', index=False)
        # exit(0)
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        if "seg" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                                     name='segment', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_zs(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-11 23:10", "2024-07-18 20:00", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-07-11 23:10", "2024-07-13 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 01:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 23:10", "2024-07-20 15:00", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        bi_manager = ChanBIManager(bi_valid_method=BiFXValidMethod.STRICT)
        zs_manager = ChanZSManager(max_level=2)
        for d in data:
            bi_manager.update(d)
            if not bi_manager.is_empty():
                zs_manager.update(bi_manager[-1])

        for bi in bi_manager:
            bi.mark_on_data()
            for ck in bi.chan_k_list:
                ck.mark_on_data()

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        if "seg" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                                     name='segment', connectgaps=True), row=1, col=1)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                     name='chan b', connectgaps=True), row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                     name='chan b', connectgaps=True), row=1, col=1)

        # zs
        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        for level in zs_manager.zs_dict:
            for zs in zs_manager.zs_dict[level]:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[level-1], width=zs.level),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
        if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy:
            zs = zs_manager.cur_zs
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level - 1], width=zs.level, dash='dash'),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()


    def test_bsp(self):
        workflow = ViewWorkflow(None, "5m", "2024-07-11 23:10", "2024-07-26 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 01:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-17 23:10", "2024-07-20 15:00", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        bi_manager = ChanBIManager(bi_valid_method=BiFXValidMethod.STRICT)
        for d in data:
            bi_manager.update(d)

        # seg_manager = ChanSegmentManager()
        zs_manager = ChanZSManager(max_level=2)
        bsp = ChanBSPoint()

        for bi in bi_manager:
            bi.mark_on_data()
            for ck in bi.chan_k_list:
                ck.mark_on_data()
            # seg_manager.update(bi)
            zs_manager.update(bi)
            for level in zs_manager.zs_dict:
                bsp.calc_bsp(zs_manager.zs_dict[level][-1], bi, bi.chan_k_list[-1])

        bsp.mark_data()
        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        if "seg" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                    name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                                     name='segment', connectgaps=True), row=1, col=1)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=1, col=1)

        if "buy_point" in df.columns:
            bdf = df[df['buy_point'].notnull()]
            fig.add_trace(go.Scatter(
                x=bdf['Datetime'],
                y=bdf['low'] * Decimal("0.96"),
                mode='markers+text',
                text=bdf["buy_point"],
                textposition="bottom center",
                marker=dict(color='green', size=4)
            ), row=1, col=1)

        if "sell_point" in df.columns:
            bdf = df[df['sell_point'].notnull()]
            fig.add_trace(go.Scatter(
                x=bdf['Datetime'],
                y=bdf['high'] * Decimal("1.04"),
                mode='markers+text',
                text=bdf["sell_point"],
                textposition="top center",
                marker=dict(color='red', size=4)
            ), row=1, col=1)

        # zs
        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        for level in zs_manager.zs_dict:
            for zs in zs_manager.zs_dict[level]:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[level-1], width=zs.level),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )

        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()


if __name__ == '__main__':
    unittest.main()
