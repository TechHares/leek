#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/16 18:22
# @Author  : shenglin.li
# @File    : job_test.py
# @Software: PyCharm
from datetime import datetime

from joblib import Parallel, delayed

from leek.runner.view import ViewWorkflow
from leek.strategy.common.decision import SMIIODecisionNode, PVTDecisionNode, STDecisionNode
from leek.strategy.strategy_voting import DecisionStrategy


def my_batch_function(batch):
    # 处理整个批次的数据
    return [item * item for item in batch]

# 假设我们有一个大的数据列表
data = list(range(100))

# 将数据分成小批次
batch_size = 10
batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]

# 使用Joblib并行执行批次函数
results = Parallel(n_jobs=-1)(delayed(my_batch_function)(batch) for batch in batches)

if __name__ == '__main__':
    workflow = ViewWorkflow(None, "15m", 1709827200000, 1710518400000, "ZRXUSDT")
    data = workflow.get_data_g()

    strategy = DecisionStrategy()
    now = datetime.now()
    # strategy.best_args(data, SMIIODecisionNode, fast_period=range(3, 15), slow_period=range(15, 40), sigma_period=range(3, 10))
    # strategy.best_args(data, PVTDecisionNode, fast_period=range(3, 15), slow_period=range(15, 40, 2))
    strategy.best_args(data, STDecisionNode, period=range(10, 26), factory=range(1, 5))
