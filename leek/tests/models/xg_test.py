#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/13 15:14
# @Author  : shenglin.li
# @File    : xg_test.py
# @Software: PyCharm
import csv
import os.path
import unittest
from datetime import datetime
from decimal import Decimal
from os import write
from pathlib import Path

import numpy as np
import pandas as pd
import tqdm
from sklearn.linear_model import LinearRegression

from leek.common import G
from leek.f.ops import Processor
from leek.runner.view import ViewWorkflow


class TestXG:

    def test_animal_k(self):
        workflow = ViewWorkflow(None, "1m", "2019-07-17 08:20", "2024-09-17 20:30", "XRP-USDT-SWAP")
        data = workflow.get_data("XRP-USDT-SWAP")

        df = pd.DataFrame([x.__json__() for x in data])
        print(len(df))
        df[["timestamp", "open", "high", "low", "close", "volume", "amount", "interval"]].to_csv("xrp.csv")

    def test_init_feature(self):
        with open(f"{Path(__file__).parent}/xrp.csv", "r") as r:
            reader = csv.DictReader(r)
            res = []
            for row in reader:
                res.append({
                    'timestamp': int(row["timestamp"]),
                    'open': Decimal(row["open"]),
                    'high': Decimal(row["high"]),
                    'low': Decimal(row["low"]),
                    'close': Decimal(row["close"]),
                    'volume': Decimal(row["volume"]),
                    'amount': Decimal(row["amount"]),
                    'interval': row["interval"]
                })
        print("数据加载完成")
        df = pd.DataFrame(res)
        eta = Decimal("0.00000000000000000000000001")
        print("数据读入完成")
        # alpha158
        # 1. 60日纯量价 无量纲化
        avg_price = df["amount"] / df["volume"].clip(lower=eta)
        for i in range(1, 61):
            df[f"CLOSE{i}"] = df["close"].shift(i) / df["close"]
            df[f"OPEN{i}"] = df["open"].shift(i) / df["close"]
            df[f"HIGH{i}"] = df["high"].shift(i) / df["close"]
            df[f"LOW{i}"] = df["low"].shift(i) / df["close"]
            df[f"VWAP{i}"] = avg_price.shift(i) / df["close"]
            df[f"VOLUME{i}"] = df["volume"].shift(i) / (df["volume"] + eta)
            print(f"计算{i}日量价特征完成")

        print("量价360计算完成")
        # 2. K线特征
        max_close_open = np.maximum(df["close"], df["open"])
        min_close_open = np.minimum(df["close"], df["open"])
        k_len = df["high"] - df["low"]
        k_body = df["close"] - df["open"]

        df["K_BODY"] = k_body / df["open"]
        df["K_LEN"] = k_len / df["open"]
        df["K_BODY1"] = k_body / (k_len + eta)
        df["K_HIGH"] = (df["high"] - max_close_open) / df["open"]
        df["K_HIGH1"] = (df["high"] - max_close_open) / (k_len + eta)
        df["K_LOW"] = (min_close_open - df["low"]) / df["open"]
        df["K_LOW1"] = (min_close_open - df["low"]) / (k_len + eta)
        df["K_SFT"] = (2 * df["close"] - df["high"] - df["low"]) / df["open"]
        df["K_SFT1"] = (2 * df["close"] - df["high"] - df["low"]) / (k_len + eta)

        print("K线特征计算完成")
        # 3. K线滚动关联
        df['LOG_VOLUME'] = np.log(df['volume'] + 1)
        df['LOG_VOLUME_RATE'] = np.log((df['volume'] / df['volume'].shift(1)) + 1)
        for i in range(1, 21):
            df[f"ROC{i}"] = df["close"].pct_change(i)
            df[f"BETA{i}"] = (df["close"] - df["close"].shift(i)) / df["close"]
        print("K线关联特征计算完成")

        # 4. 技术指标
        up_k = df["close"] > df["close"].shift(1)
        down_k = df["close"] < df["close"].shift(1)
        gain = (df['close'] - df['close'].shift(1)).clip(lower=0)
        loss = (df['close'].shift(1) - df['close']).clip(lower=0)
        pct_change = df['close'].pct_change()
        weighted_price_change = pct_change * df['volume']
        abs_change = (df['close'] - df['close'].shift(1)).abs().clip(lower=eta)
        volume_change = df['volume'] - df['volume'].shift(1)
        for i in [3, 5, 7, 10, 12, 15, 20, 30, 60]:
            df[f'SMA{i}'] = df['close'].rolling(window=i).mean()
            df[f'EMA{i}'] = df['close'].ewm(span=i, adjust=False).mean()
            df[f'STD{i}'] = df['close'].rolling(window=i).std()
            df[f'MAX{i}'] = df['high'].rolling(window=i).max() / df["close"]
            df[f'MIN{i}'] = df['low'].rolling(window=i).min() / df["close"]
            df[f'RSV{i}'] = (df["close"] - df[f'MIN{i}']) / (df[f'MAX{i}'] - df[f'MIN{i}'] + eta)
            df[f'IMAX{i}'] = (df.index.max() - df['high'].idxmax()) % i
            df[f'IMIN{i}'] = (df.index.max() - df['low'].idxmin()) % i
            df[f'IMXD{i}'] = (df['high'].idxmax() - df['low'].idxmin()) % i
            df[f'CORR{i}'] = df['close'].rolling(window=i).corr(df['LOG_VOLUME'])
            df[f'CORD{i}'] = (df['close'] / df['close'].shift(1)).rolling(window=i).corr(df['LOG_VOLUME_RATE'])
            df[f'CNTP{i}'] = up_k.astype(int).rolling(window=i).mean()
            df[f'CNTN{i}'] = down_k.astype(int).rolling(window=i).mean()
            df[f'CNTD{i}'] = df[f'CNTP{i}'] - df[f'CNTN{i}']
            df[f'SUMP{i}'] = gain.rolling(window=i).sum() / abs_change.rolling(window=i).sum()
            df[f'SUMN{i}'] = loss.rolling(window=i).sum() / abs_change.rolling(window=i).sum()
            df[f'SUMD{i}'] = df[f'SUMP{i}'] - df[f'SUMN{i}']
            df[f'VMA{i}'] = df['volume'].rolling(window=i).mean() / (df["volume"] + eta)
            df[f'VSTD{i}'] = df['volume'].rolling(window=i).std() / (df["volume"] + eta)
            abs_weighted_price_change = weighted_price_change.abs()
            df[f'WVMA{i}'] = abs_weighted_price_change.rolling(window=i).std() / abs_weighted_price_change.rolling(
                window=i).mean().clip(lower=eta)
            df[f'VSUMP{i}'] = volume_change.clip(lower=eta).rolling(window=i).sum() / volume_change.abs().rolling(
                window=i).sum().clip(lower=eta)
            df[f'VSUMN{i}'] = volume_change.clip(upper=0).rolling(window=i).sum().abs() / volume_change.abs().rolling(
                window=i).sum().clip(lower=eta)
            df[f'VSUMD{i}'] = df[f'VSUMP{i}'] - df[f'VSUMN{i}']
            df[f'RANK{i}'] = df['close'].rolling(window=i).rank(pct=True)
            df[f'QTLU{i}'] = df['close'].rolling(window=i).quantile(0.8) / df['close']
            df[f'QTLD{i}'] = df['close'].rolling(window=i).quantile(0.2) / df['close']

            print(f"windows={i}, 技术指标特征计算完成")
        print("技术指标特征计算完成")
        # 5. 回归型指标
        for i in [3, 5, 7, 10, 12, 15, 20, 30, 60]:
            df[f'RSQR{i}'] = None  # R-sqaure
            for j in range(len(df) - i + 1):
                # 获取当前窗口的数据
                X = df.index[j:j + i]  # idx作为自变量
                Y = df['close'].iloc[j:j + i]  # 收盘价作为因变量

                model = LinearRegression()
                model.fit(X.values.reshape(-1, 1), Y)

                r_squared = model.score(X.values.reshape(-1, 1), Y)
                df.at[i + j - 1, f'RSQR{j}'] = r_squared

                residuals = Y - model.predict(X)
                df.loc[i + j - 1, f'RESI{j}'] = residuals / df['close'].iloc[i + j - 1]

        print("完成")
        df.to_csv(f"features.csv")

    def test_init_feature_by_expression(self):
        features =  {}
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
            features[f"roll_cord{window}"] = f"corr($close/ref($close,1), log($volume/(ref($volume, 1) + 1e-20)+1), {window})"
            features[f"roll_cntp{window}"] = f"count($close>ref($close, 1), {window}) / {window}"
            features[f"roll_cntn{window}"] = f"count($close<ref($close, 1), {window}) / {window}"
            features[f"roll_cntd{window}"] = f"(count($close>ref($close, 1), {window}) - count($close<ref($close, 1), {window})) / {window}"
            features[f"roll_sump{window}"] = f"sum(larger($close-ref($close, 1), 0), {window})/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
            features[f"roll_sumn{window}"] = f"sum(larger(ref($close, 1)-$close, 0), {window})/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
            features[f"roll_sumd{window}"] = f"(sum(larger($close-ref($close, 1), 0), {window}) - sum(larger(ref($close, 1)-$close, 0), {window}))/(sum(abs($close-ref($close, 1)), {window})+1e-12)"
            features[f"roll_vma{window}"] = f"sma($volume, {window}) / ($volume+1e-20)"
            features[f"roll_vstd{window}"] = f"std($volume, {window}) / ($volume+1e-20)"
            features[f"roll_vwma{window}"] = f"std(abs($close/ref($close, 1)-1)*$volume, {window})/(sma(abs($close/ref($close, 1)-1)*$volume, {window})+1e-20)"
            features[f"roll_vsump{window}"] = f"sum(larger($volume-ref($volume, 1), 0), {window}) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"
            features[f"roll_vsumn{window}"] = f"sum(larger(ref($volume, 1)-$volume, 0), {window}) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"
            features[f"roll_vsumd{window}"] = f"(sum(larger($volume-ref($volume, 1), 0), {window}) - sum(larger(ref($volume, 1)-$volume, 0), {window})) / (sum(abs($volume-ref($volume, 1)), {window})+1e-20)"
        process = Processor.wrapper_processor(features)
        with (open(f"{Path(__file__).parent}/xrp.csv", "r") as r):
            reader = csv.DictReader(r)
            writer = None
            l = list(reader)
            it = tqdm.tqdm(total=len(l))
            with open(f"{Path(__file__).parent}/xrp_features.csv", "w") as w:
                for row in l:
                    it.update()
                    k = G(**{
                        'timestamp': int(row["timestamp"]),
                        'open': float(row["open"]),
                        'high': float(row["high"]),
                        'low': float(row["low"]),
                        'close': float(row["close"]),
                        'volume': float(row["volume"]),
                        'amount': float(row["amount"]),
                        'interval': row["interval"]
                    })
                    process(k)

                    if writer is None:
                        writer = csv.DictWriter(w, fieldnames=list(k.__json__().keys()))
                        writer.writeheader()
                    writer.writerow(k.__json__())

if __name__ == '__main__':
    # TestXG().test_animal_k()
    # TestXG().test_init_feature()
    start = datetime.now()
    TestXG().test_init_feature_by_expression()
    print(datetime.now() - start)
