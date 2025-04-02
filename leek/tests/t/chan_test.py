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
import plotly.io as pio
from leek.t.chan.chan import Chan
from leek.t.chan.dr import ChanDRManager
from leek.trade.trade import PositionSide

class TestChan(unittest.TestCase):

    def test_animal_k(self):
        workflow = ViewWorkflow(None, "5m", "2024-07-17 08:20", "2024-07-17 20:30", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')



    def test_k(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-18 23:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-12-16 14:20", "2024-12-16 15:00", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
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
        # workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2024-12-20 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "1m", "2025-03-06 23:10", "2025-03-07 20:00", "CRV-USDT-SWAP")
        workflow = ViewWorkflow(None, "1m", "2025-03-07 08:10", "2025-03-07 10:20", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
        bi_manager = ChanBIManager()
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
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='bi_idx'),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='bi_idx'),
                      row=2, col=1)
        fig.add_trace(go.Scatter(
            x=df['Datetime'],
            y=df['high'] * Decimal("1.01"),
            mode='markers+text',
            text=df["ck_idx"],
            marker=dict(color='green', size=4)
        ), row=2, col=1)
        fig.add_trace(go.Candlestick(x=df['Datetime'],
                                     open=df['chan_open'],
                                     high=df['chan_high'],
                                     low=df['chan_low'],
                                     close=df['chan_close'],
                                     name=df.iloc[0]["symbol"]), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
        fig.update_layout(height=800, width=1200)
        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_seg(self):
        # workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2024-12-20 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "1m", "2025-03-01 23:10", "2025-03-03 20:00", "CRV-USDT-SWAP")
        workflow = ViewWorkflow(None, "1m", "2025-03-06 23:10", "2025-03-07 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "1m", "2025-03-06 23:10", "2025-03-08 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2024-12-17 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-12-30 23:10", "2025-01-07 20:00", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
        bi_manager = ChanBIManager()
        seg_manager = ChanSegmentManager()
        for d in data:
            bi = bi_manager.update(d)
            if bi:
                seg_manager.update_bi(bi)

        # for bi in bi_manager:
        #     seg_manager.update_bi(bi)
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
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df["seg_value"], mode='text', text=df["seg_idx"], name='seg_idx'),
                row=1, col=1)

            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                                     name='segment', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                 name='chan b', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                 name='chan b', connectgaps=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='bi_idx'),
                      row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_zs(self):
        workflow = ViewWorkflow(None, "1m", "2025-03-01 23:10", "2025-03-02 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2024-12-17 20:00", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
        bi_manager = ChanBIManager()
        seg_manager = ChanSegmentManager()
        zs_manager = ChanZSManager(max_level=2, allow_similar_zs=False)
        for d in data:
            bi = bi_manager.update(d)
            # if bi:
            #     zs_manager.update(bi)

        for seg in seg_manager:
            # print(seg.pre.idx if seg.pre else "None", "<-", seg.idx, "->",  seg.next.idx if seg.next else "None")
            seg.mark_on_data()

        for bi in bi_manager:
            zs_manager.update(bi)
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
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df["seg_value"], mode='text', text=df["seg_idx"], name='seg_idx'),
                row=1, col=1)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                     name='chan b', connectgaps=True), row=1, col=1)
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='seg_idx'),
                row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                                     name='chan b', connectgaps=True), row=1, col=1)


        # zs
        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        for zs in zs_manager.zs_list:
            print(f"level={zs.level}", f"into={zs.into_ele.idx}", f"zs={len(zs.element_list)}", f"out={zs.out_ele.idx if zs.out_ele else None}")
        for zs in zs_manager.zs_list:
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level+1),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy:
            zs = zs_manager.cur_zs
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level+1, dash='dash'),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()


    def test_bsp(self):
        # workflow = ViewWorkflow(None, "5m", "2024-07-15 12:10", "2024-07-18 10:00", "ULTI-USDT-SWAP")
        workflow = ViewWorkflow(None, "5m", "2024-07-18 23:10", "2024-07-21 20:00", "ULTI-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-07-11 23:10", "2024-07-28 20:00", "ULTI-USDT-SWAP")
        data = workflow.get_data("ULTI-USDT-SWAP")
        bi_manager = ChanBIManager()
        zs_manager = ChanZSManager(max_level=2, enable_expand=False, enable_stretch=False)
        bsp = ChanBSPoint(b1_zs_num=1)
        for d in data:
            bi_manager.update(d)
            if not bi_manager.is_empty():
                bi = bi_manager[-1]
                zs_manager.update(bi)
                bsp.calc_bsp(zs_manager.cur_zs if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy else None,
                             bi, bi.chan_k_list[-1])

        # seg_manager = ChanSegmentManager()

        zs_manager1 = ChanZSManager(max_level=2, enable_expand=False, enable_stretch=False)
        bsp1 = ChanBSPoint(b1_zs_num=1, max_interval_k=20000)
        for bi in bi_manager:
            bi.mark_on_data()
            for ck in bi.chan_k_list:
                ck.mark_on_data()
            # seg_manager.update(bi)
            zs_manager1.update(bi)
            if bi.next is not None:
                cur_zs = zs_manager1.cur_zs if zs_manager1.cur_zs is not None and zs_manager1.cur_zs.is_satisfy else None
                if cur_zs is None and 1 in zs_manager1.zs_dict:
                    zsd = zs_manager1.zs_dict[1]
                    if len(zsd) > 0:
                        cur_zs = zsd[-1]

                bsp1.calc_bsp(cur_zs, bi.next, bi.next.chan_k_list[2])


        bsp.mark_data()
        bsp1.b1 = [b for b in bsp1.b1 if b in bsp.b1]
        bsp1.s1 = [s for s in bsp1.s1 if s in bsp.s1]
        bsp1.b2 = [b for b in bsp1.b2 if b in bsp.b2]
        bsp1.s2 = [s for s in bsp1.s2 if s in bsp.s2]
        bsp1.b3 = [b for b in bsp1.b3 if b in bsp.b3]
        bsp1.s3 = [s for s in bsp1.s3 if s in bsp.s3]
        bsp1.mark_data("_")



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
                mode='text',
                text=bdf["buy_point"],
                textposition="bottom center",
                marker=dict(color='green', size=4)
            ), row=1, col=1)

        if "sell_point" in df.columns:
            bdf = df[df['sell_point'].notnull()]
            fig.add_trace(go.Scatter(
                x=bdf['Datetime'],
                y=bdf['high'] * Decimal("1.04"),
                mode='text',
                text=bdf["sell_point"],
                textposition="top center",
                marker=dict(color='red', size=4)
            ), row=1, col=1)
        if "buy_point_" in df.columns:
            bdf = df[df['buy_point_'].notnull()]
            fig.add_trace(go.Scatter(
                x=bdf['Datetime'],
                y=bdf['low'] * Decimal("0.96"),
                mode='markers+text',
                text=bdf["buy_point_"],
                textposition="bottom center",
                marker=dict(color='green', size=4)
            ), row=1, col=1)

        if "sell_point_" in df.columns:
            bdf = df[df['sell_point_'].notnull()]
            fig.add_trace(go.Scatter(
                x=bdf['Datetime'],
                y=bdf['high'] * Decimal("1.04"),
                mode='markers+text',
                text=bdf["sell_point_"],
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

    def test_dr(self):
        workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2025-01-30 20:00", "CRV-USDT-SWAP")
        # workflow = ViewWorkflow(None, "5m", "2024-12-15 23:10", "2024-12-17 20:00", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
        bi_manager = ChanBIManager()
        seg_manager = ChanSegmentManager()
        zs_manager = ChanZSManager(max_level=2, allow_similar_zs=True)
        dr_manager = ChanDRManager()
        drzs_manager = ChanZSManager(max_level=2, allow_similar_zs=True)
        tmp_dr = None
        tmp_zs = None
        for d in data:
            bi = bi_manager.update(d)
            if bi:
                seg = seg_manager.update_bi(bi)
                if seg:
                    zs_manager.update(seg)
                    for zs in zs_manager.zs_list:
                        if tmp_zs is None or zs.idx >= tmp_zs.idx:
                            dr_manager.update(zs)
                            tmp_zs = zs
                    if zs_manager.cur_zs:
                        dr_manager.update(zs_manager.cur_zs)
                        tmp_zs = zs_manager.cur_zs

                    for dr in dr_manager.dr_list:
                        if tmp_dr is None or dr.idx >= tmp_dr.idx:
                            drzs_manager.update(dr)
                            tmp_dr = dr

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        if "seg" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                           name='segment', connectgaps=True), row=1, col=1)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                     name='chan b', connectgaps=True), row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                           name='chan b', connectgaps=True), row=1, col=1)

        if "dr" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dr'], mode='lines', line=dict(color='darkblue', width=3),
                                     name='chan dr', connectgaps=True), row=1, col=1)
        if "dr_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['dr_'], mode='lines', line=dict(color='darkblue', width=3, dash='dash'),
                           name='chan dr', connectgaps=True), row=1, col=1)

        fig.add_trace(go.Scatter(x=df['Datetime'], y=df["seg_value"], mode='text', text=df["seg_idx"], name='seg_idx'),
                      row=1, col=1)
        # zs
        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        # for zs in zs_manager.zs_list:
        #     print(f"level={zs.level}", f"into={zs.into_ele.idx}", f"zs={len(zs.element_list)}",
        #           f"out={zs.out_ele.idx if zs.out_ele else None}")
        for zs in zs_manager.zs_list:
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level + 1),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )

        for zs in drzs_manager.zs_list:
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level + 3),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy:
            zs = zs_manager.cur_zs
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level + 1, dash='dash'),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        if drzs_manager.cur_zs is not None and drzs_manager.cur_zs.is_satisfy:
            zs = drzs_manager.cur_zs
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                line=dict(color=colors[zs.level], width=zs.level + 3, dash='dash'),
                fillcolor=None,  # 透明填充，只显示边框
                name='Highlight Area'
            )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()

    def test_chan(self):
        workflow = ViewWorkflow(None, "1m", "2025-03-01 23:10", "2025-03-25 20:00", "CRV-USDT-SWAP")
        data = workflow.get_data("CRV-USDT-SWAP")
        chan = Chan(bi_zs=True, seg=True, seg_zs=True, dr=True, dr_zs=True, exclude_equal=False, zs_max_level=2, allow_similar_zs=True)

        for d in data:
            chan.update(d)
        chan.mark_on_data()

        df = pd.DataFrame([x.__json__() for x in data])
        df['Datetime'] = pd.to_datetime(df['timestamp'] + 8 * 60 * 60 * 1000, unit='ms')
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        if "seg" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df["seg_value"], mode='text', text=df["seg_idx"], name='seg_idx'),
                row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['seg'], mode='lines', line=dict(color='blue', width=2),
                                     name='segment', connectgaps=True), row=1, col=1)
        if "seg_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['seg_'], mode='lines', line=dict(color='blue', width=2, dash='dash'),
                           name='segment', connectgaps=True), row=1, col=1)

        if "bi" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df["bi_value"], mode='text', text=df["bi_idx"], name='bi_idx'),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['bi'], mode='lines', line=dict(color='black', width=1),
                                     name='chan b', connectgaps=True), row=1, col=1)
        if "bi_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['bi_'], mode='lines', line=dict(color='black', width=1, dash='dash'),
                           name='chan b', connectgaps=True), row=1, col=1)

        if "dr" in df.columns:
            fig.add_trace(go.Scatter(x=df['Datetime'], y=df['dr'], mode='lines', line=dict(color='darkblue', width=3),
                                     name='chan dr', connectgaps=True), row=1, col=1)
        if "dr_" in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Datetime'], y=df['dr_'], mode='lines',
                           line=dict(color='darkblue', width=3, dash='dash'),
                           name='chan dr', connectgaps=True), row=1, col=1)


        # zs
        colors = ["orange", "skyblue", "lightgreen", "gainsboro", "darkblue"]
        if chan.seg_zs:
            for zs in chan.zs_manager.zs_list:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=zs.level + 1),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
            if chan.zs_manager.cur_zs is not None and chan.zs_manager.cur_zs.is_satisfy:
                zs = chan.zs_manager.cur_zs
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=zs.level + 1, dash='dash'),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
        if chan.dr_zs:
            for zs in chan.drzs_manager.zs_list:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=zs.level + 3),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
            if chan.drzs_manager.cur_zs is not None and chan.drzs_manager.cur_zs.is_satisfy:
                zs = chan.drzs_manager.cur_zs
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=zs.level + 3, dash='dash'),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
        if chan.bi_zs:
            for zs in chan.bizs_manager.zs_list:
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=1),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
            if chan.bizs_manager.cur_zs is not None and chan.bizs_manager.cur_zs.is_satisfy:
                zs = chan.bizs_manager.cur_zs
                fig.add_shape(
                    type='rect',
                    x0=pd.to_datetime([zs.start_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y0=zs.down_line,
                    x1=pd.to_datetime([zs.end_timestamp + 8 * 60 * 60 * 1000], unit="ms")[0], y1=zs.up_line,
                    line=dict(color=colors[zs.level], width=1, dash='dash'),
                    fillcolor=None,  # 透明填充，只显示边框
                    name='Highlight Area'
                )
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        workflow.draw(fig=fig, df=df)
        fig.show()

if __name__ == '__main__':
    unittest.main()
