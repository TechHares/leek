#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/11 20:14
# @Author  : shenglin.li
# @File    : xg.py
# @Software: PyCharm
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split as TTS
from sklearn.metrics import roc_auc_score, accuracy_score, recall_score

from leek.common import config


def xa(a):
    print(a)


def data_process():
    file = f"{config.DATA_DIR}/features.csv"
    df = pd.read_csv(file, dtype={'label': "category", "bsp": "category", "chan_fx_type": "category"})
    print("数据读取完成")
    x_train, x_test, y_train, y_test = TTS(df.drop('label', axis=1), df['label'], test_size=0.1)
    # 转换为DMatrix格式
    print("数据分割完成")
    dtrain = xgb.DMatrix(x_train, label=y_train, enable_categorical=True)
    dtest = xgb.DMatrix(x_test, label=y_test, enable_categorical=True)
    print("数据转换dmatrix完成")
    dtrain.save_binary(f"{config.DATA_DIR}/train.dat")
    dtest.save_binary(f"{config.DATA_DIR}/test.dat")

def train_model():
    dtrain = xgb.DMatrix(f"{config.DATA_DIR}/train.dat")
    y_train = dtrain.get_label()
    # XGBoost参数
    params = {
        'objective': 'binary:logistic',
        'max_depth': 6,
        'eta': 0.02,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'eval_metric': 'auc',
        'scale_pos_weight': len(y_train[y_train == 0]) / len(y_train[y_train == 1]),
    }
    print(f"训练样本 0样本数：{len(y_train[y_train == 0])}， 1样本数：{len(y_train[y_train == 1])}, scale_pos_weight:", len(y_train[y_train == 0]) / len(y_train[y_train == 1]))
    # 训练模型
    num_round = 500
    bst = xgb.train(params, dtrain, num_round)
    bst.save_model(f"{config.DATA_DIR}/model.json")

def predict():
    dtest = xgb.DMatrix(f"{config.DATA_DIR}/test.dat")
    y_test = dtest.get_label()

    bst = xgb.Booster()
    bst.load_model(f"{config.DATA_DIR}/model.json")

    # 获取特征评分
    scores = bst.get_score(importance_type='weight')
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    for feature, score in sorted_scores:
        print(f"{feature}: {score}")

    # 预测
    preds = bst.predict(dtest)

    # 评估模型
    auc = roc_auc_score(y_test, preds)
    predictions = (preds > 0.5).astype(int)
    # 计算 0 和 1 的个数
    num_0 = np.sum(predictions == 0)
    num_1 = np.sum(predictions == 1)
    print(f"实际结果 0样本数：{len(y_test[y_test == 0])}， 1样本数：{len(y_test[y_test == 1])}")
    print(f"预测结果 0的个数：{num_0}，1的个数：{num_1}")
    score = accuracy_score(y_test.astype(int), predictions)
    print(f'AUC: {auc:.2f}')
    print(f'accuracy_score: {score:.4f}')
    # 计算真正例率
    recall = recall_score(y_test.astype(int), predictions)
    print(f'Recall: {recall:.4f}')


if __name__ == '__main__':
    # data_process()
    # train_model()
    predict()
