#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/16 18:22
# @Author  : shenglin.li
# @File    : job_test.py
# @Software: PyCharm
import copy
import csv
import json
from decimal import Decimal
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from leek.common.utils import decimal_quantize
from leek.runner.view import ViewWorkflow
from leek.strategy.common.decision import OBVDecisionNode, PVTDecisionNode, STDecisionNode, MADecisionNode, \
    MACDDecisionNode, VolumeDecisionNode, SMIIODecisionNode


def best_args(evaluation_data, decision_cls, **kwargs):
    keys = kwargs.keys()
    values = [kwargs[key] for key in keys]
    combinations = list(product(*values))
    r = []
    for combination in combinations:
        eval_args = dict(zip(keys, combination))
        decision = decision_cls(**eval_args)
        trade_count, profit = decision.evaluation(copy.deepcopy(evaluation_data), Decimal("0.0005"))
        r.append((trade_count, eval_args, str(decimal_quantize(profit, 6))))
    return r

def compute_task(tsk):
    data, number, moving_period = tsk
    return best_args(data, SMIIODecisionNode, fast_period=[number], slow_period=range(max(15, number), 155), sigma_period=[moving_period])


def computed(file, moving_period):
    workflow = ViewWorkflow(None, "5m", 1705198187517, 1712974187517, "ZRXUSDT")
    d = workflow.get_data_g()
    tasks = [(d, i, moving_period) for i in range(3, 62)]
    results = Parallel(n_jobs=-1)(delayed(compute_task)(task) for task in tasks)

    with open(file, "w") as f:
        w = csv.DictWriter(f, fieldnames=["fast_period", "slow_period", "trade_count", "profit"], lineterminator='\n')
        r = [{
            "fast_period": x[1]["fast_period"],
            "slow_period": x[1]["slow_period"],
            "trade_count": x[0],
            "profit": x[2]
        } for xs in results for x in xs]
        print(len(r))
        w.writeheader()
        w.writerows(r)


if __name__ == '__main__':
    for i in range(3, 25):
        print("smiio", i)
        computed(f"smiio_{i}.csv", i)
    # import matplotlib
    # matplotlib.use('TkAgg')
    # import matplotlib.pyplot as plt
    # from mpl_toolkits.mplot3d import Axes3D
    # from scipy.interpolate import griddata
    # df = pd.read_csv("ma.csv")
    #
    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')
    #
    # # 从DataFrame中提取X、Y、Z坐标数据
    # x = df['fast_period']
    # y = df['slow_period']
    # z = df['profit']
    #
    # xgrid = np.linspace(min(x), max(x), 100)
    # ygrid = np.linspace(min(y), max(y), 100)
    #
    # # 使用np.meshgrid生成网格矩阵
    # X, Y = np.meshgrid(xgrid, ygrid)
    #
    # # 使用griddata进行插值
    # Z = griddata((x, y), z, (X, Y), method='cubic')
    #
    # # 绘制三维散点图
    # ax.plot_surface(X, Y, Z, cmap='viridis')
    #
    # # 设置坐标轴标签
    # ax.set_xlabel('fast_period')
    # ax.set_ylabel('slow_period')
    # ax.set_zlabel('profit')

    # 显示图形
    plt.savefig("ma.png")
    plt.show()

    print(df)

