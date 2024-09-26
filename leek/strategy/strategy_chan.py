#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 20:18
# @Author  : shenglin.li
# @File    : strategy_chan.py
# @Software: PyCharm
import pandas as pd
from twisted.protocols.amp import Decimal

from leek.common import config
from leek.f.ops import Processor
from leek.strategy import BaseStrategy
from leek.strategy.common import PositionDirectionManager
from leek.strategy.common.strategy_common import PositionRateManager
from leek.strategy.common.strategy_filter import JustFinishKData
from leek.t import *
import xgboost as xgb

from leek.trade.trade import PositionSide


class ChanStrategy(PositionRateManager, PositionDirectionManager, JustFinishKData, BaseStrategy):
    verbose_name = "缠论V1(xgb辅助版)"

    """
    缠论：禅中说缠理论实现
    参考文献地址： http://www.fxgan.com/chan_fenlei/index.htm#@
                 https://www.bilibili.com/read/cv16235114/
                 https://github.com/DYLANFREE/huangjun.work/blob/master/README.md
                 https://xueqiu.com/1468953003/78447616
    
    """
    features = {}
    for i in range(1, 60):
        features[f"vp_close{i}"] = f'ref($close, {i}) / $close'
        features[f"vp_open{i}"] = f'ref($open, {i}) / $close'
        features[f"vp_high{i}"] = f'ref($high, {i}) / $close'
        features[f"vp_low{i}"] = f'ref($low, {i}) / $close'
        features[f"vp_vwap{i}"] = f'ref($vwap, {i}) / $close'
        features[f"vp_volume{i}"] = f'ref($volume, {i}) / ($volume + 1e-20)'
    # k线
    features["k_mid"] = f"($close-$open)/$open"
    features["k_len"] = f"($high-$low)/$open"
    features["k_mid2"] = f"($close-$open)/($high-$low + 1e-20)"
    features["k_up"] = f"($high-larger($open, $close))/$open"
    features["k_up2"] = f"($high-larger($open, $close))/($high-$low + 1e-20)"
    features["k_low"] = f"(smaller($open, $close)-$low)/$open"
    features["k_low2"] = f"(smaller($open, $close)-$low)/($high-$low + 1e-20)"
    features["k_sft"] = f"(2*$close-$high-$low)/$open"
    features["k_sft2"] = f"(2*$close-$high-$low)/($high-$low + 1e-20)"
    for window in [5, 10, 20, 30, 60]:
        features[f"roll_sma{window}"] = f"sma($close, {window}) / $close"
        features[f"roll_std{window}"] = f"std($close, {window}) / $close"
        features[f"roll_beta{window}"] = f"($close - ref($close, {window})) / $close"
        features[f"roll_high{window}"] = f"max($high, {window}) / $close"
        features[f"roll_low{window}"] = f"min($low, {window}) / $close"
        features[f"roll_beta{window}"] = f"slope($close, {window}) / $close"
        features[f"roll_rsqr{window}"] = f"r2($close, {window})"
        features[f"roll_resi{window}"] = f"resi($close, {window})"
        features[f"roll_qltu{window}"] = f"quantile($close, {window}, 0.8) / $close"
        features[f"roll_qltd{window}"] = f"quantile($close, {window}, 0.2) / $close"
        features[f"roll_rank{window}"] = f"rank($close, {window})"
        features[f"roll_rsv{window}"] = f"($close-min($low, {window}))/(max($high, {window})-min($low, {window})+1e-12)"
        features[f"roll_idxmax{window}"] = f"idxmax($high, {window}) / {window}"
        features[f"roll_idxmin{window}"] = f"idxmin($low, {window}) / {window}"
        features[f"roll_imxd{window}"] = f"(idxmin($low, {window}) - idxmin($low, {window})) / {window}"
        features[f"roll_corr{window}"] = f"corr($close, log($volume+1), {window})"
        features[
            f"roll_cord{window}"] = f"corr($close/ref($close,1), log($volume/(ref($volume, 1) + 1e-20)+1), {window})"
        features[f"roll_cntp{window}"] = f"count($close>ref($close, 1), {window}) / {window}"
        features[f"roll_cntn{window}"] = f"count($close<ref($close, 1), {window}) / {window}"
        features[
            f"roll_cntd{window}"] = f"(count($close>ref($close, 1), {window}) - count($close<ref($close, 1), {window})) / {window}"
        features[
            f"roll_sump{window}"] = f"sum(larger($close-ref($close, 1), 0), {window})/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
        features[
            f"roll_sumn{window}"] = f"sum(larger(ref($close, 1)-$close, 0), {window})/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
        features[
            f"roll_sumd{window}"] = f"(sum(larger($close-ref($close, 1), 0), {window}) - sum(larger(ref($close, 1)-$close, 0), {window}))/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
        features[f"roll_vma{window}"] = f"sma($volume, {window}) / ($volume+1e-20)"
        features[f"roll_vstd{window}"] = f"std($volume, {window}) / ($volume+1e-20)"
        features[
            f"roll_vwma{window}"] = f"std(abs($close/ref($close, 1)-1)*$volume, {window})/(sma(abs($close/ref($close, 1)-1)*$volume, {window})+1e-20)"
        features[
            f"roll_vsump{window}"] = f"sum(larger($volume-ref($volume, 1), 0), {window}) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"
        features[
            f"roll_vsumn{window}"] = f"sum(larger(ref($volume, 1)-$volume, 0), {window}) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"
        features[
            f"roll_vsumd{window}"] = f"(sum(larger($volume-ref($volume, 1), 0), {window}) - sum(larger(ref($volume, 1)-$volume, 0), {window})) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"

    def __init__(self, bi_valid_method: BiFXValidMethod|int =BiFXValidMethod.STRICT, zs_max_level: int = 2,
                 enable_expand: bool = False, enable_stretch: bool = False, b1_zs_num=1, model_file="chan.json"):
        self.bi_valid_method = BiFXValidMethod(bi_valid_method)
        self.zs_max_level = int(zs_max_level)
        self.enable_expand = str(enable_expand).lower() in ["true", 'on', 'open', '1']
        self.enable_stretch = str(enable_stretch).lower() in ["true", 'on', 'open', '1']
        self.b1_zs_num = int(b1_zs_num)
        self.model_file = model_file
        self.bst = xgb.Booster()
        self.bst.load_model(f"{config.DATA_DIR}/models/{self.model_file}")

    def _calculate(self):
        if self.g.bi_manager is None:
            self.g.bi_manager = ChanBIManager(bi_valid_method=self.bi_valid_method)
            self.g.zs_manager = ChanZSManager(max_level=self.zs_max_level,
                                            enable_expand=self.enable_expand,
                                            enable_stretch=self.enable_stretch)
            self.g.bsp = ChanBSPoint(b1_zs_num=self.b1_zs_num)
            self.g.features = Processor.wrapper_processor(ChanStrategy.features)  # todo 特征暂时不可选


        bi_manager = self.g.bi_manager
        zs_manager = self.g.zs_manager
        bsp = self.g.bsp
        self.g.features(self.market_data)
        bi_manager.update(self.market_data)
        if not bi_manager.is_empty():
            bi = bi_manager[-1]
            k = bi.chan_k_list[-1]
            zs_manager.update(bi)
            zs = zs_manager.cur_zs if zs_manager.cur_zs is not None and zs_manager.cur_zs.is_satisfy else None
            bsp.calc_bsp(zs, bi, bi.chan_k_list[-1])
            if k in bsp.b1:
                self.market_data.bsp = "b1"
            if k in bsp.s1:
                self.market_data.bsp = "s1"
            if k in bsp.b2:
                self.market_data.bsp = "b2"
            if k in bsp.s2:
                self.market_data.bsp = "s2"
            if k in bsp.b3:
                self.market_data.bsp = "b3"
                if k in bsp.b2:
                    self.market_data.bsp = "b2+b3"
            if k in bsp.s3:
                self.market_data.bsp = "s3"
                if k in bsp.s2:
                    self.market_data.bsp = "s2+s3"
            if len(bi.chan_k_list) > 3:
                fx = ChanFXManager()
                fx.next(bi.chan_k_list[-3])
                fx.next(bi.chan_k_list[-2])
                fx.next(bi.chan_k_list[-1])
                def normalization(v):
                    return float(v / self.market_data.open)
                if fx.fx is not None:
                    self.market_data.chan_high = normalization(bi.chan_k_list[-1].high)
                    self.market_data.chan_low = normalization(bi.chan_k_list[-1].low)
                    self.market_data.chan_fx_type = normalization(fx.fx.value)
                    self.market_data.chan_fx_score = normalization(fx.score)
                    self.market_data.chan_fx_left_high = normalization(fx.left.high)
                    self.market_data.chan_fx_left_low = normalization(fx.left.low)
                    self.market_data.chan_fx_point_high = normalization(fx.point.high)
                    self.market_data.chan_fx_point_low = normalization(fx.point.low)
                    self.market_data.chan_fx_right_high = normalization(fx.right.high)
                    self.market_data.chan_fx_right_low = normalization(fx.point.low)

    def handle(self):
        self._calculate()
        bsp = self.market_data.bsp
        if bsp is None:
            return
        bst = self.bst
        df = pd.DataFrame([self.market_data.__json__()], columns=bst.feature_names)
        # for col in df.select_dtypes(include=['decimal']).columns:
        #     df[col] = df[col].astype(float)
        for col in ["chan_fx_type", "bsp"]:
            df[col] = df[col].astype("category")
        dmatrix = xgb.DMatrix(df, enable_categorical=True)
        preds = bst.predict(dmatrix)
        if preds[0] < 0.5:
            return
        if bsp.startswith("b"): # 开多形态
            self.buy(bsp)
        else: # 开空形态
            self.sell(bsp)

    def buy(self, bsp):
        if self.have_position(): # 有仓位
            if self.is_short_position(): # 空头仓位
                self.close_position()
            if self.is_long_position(): # 多头仓位
                ...
        elif self.can_long():
            self.create_order(PositionSide.LONG, position_rate=self.max_single_position, memo=str(bsp))

    def sell(self, bsp):
        if self.have_position():  # 有仓位
            if self.is_short_position():  # 空头仓位
                ...
            if self.is_long_position():  # 多头仓位
                self.close_position()
        elif self.can_short():
            self.create_order(PositionSide.SHORT, position_rate=self.max_single_position, memo=str(bsp))


if __name__ == '__main__':
    pass
