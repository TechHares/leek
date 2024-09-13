#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/13 15:14
# @Author  : shenglin.li
# @File    : xg_test.py
# @Software: PyCharm
import csv
import os.path
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
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


if __name__ == '__main__':
    # TestXG().test_animal_k()
    TestXG().test_init_feature()
