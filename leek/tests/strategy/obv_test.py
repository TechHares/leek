#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import multiprocessing
from decimal import Decimal
from itertools import product

from leek.common import logger
from leek.runner.view import ViewWorkflow
from leek.strategy.common.decision import OBVDecisionNode


def best_args(evaluation_data, decision_cls, **kwargs):
    keys = kwargs.keys()
    values = [kwargs[key] for key in keys]
    combinations = list(product(*values))
    best_args = {}
    best_trade_count = 0
    best_profit = -1
    r = []
    for combination in combinations:
        eval_args = dict(zip(keys, combination))
        decision = decision_cls(**eval_args)
        trade_count, profit = decision.evaluation(copy.deepcopy(evaluation_data), Decimal("0.0005"))
        if trade_count == 0:
            continue
        if profit > 2.1:
            r.append((trade_count, eval_args, profit))
        if profit > best_profit:
            best_args = eval_args
            best_trade_count = trade_count
            best_profit = profit
        logger.info("decision_cls:{}, trade_count={}, profit:{}, args={}"
                    .format(decision_cls.__name__, trade_count, profit, eval_args))
    logger.info("decision_cls:{}, best_trade_count:{}, best_profit:{}, args={}"
                .format(decision_cls.__name__, best_trade_count, best_profit - 1, best_args))
    # return best_args, best_profit - 1
    return r


def compute_task(tsk):
    data, number = tsk
    return best_args(data, OBVDecisionNode, fast_period=[number], slow_period=range(max(15, number), 144))


if __name__ == '__main__':
    workflow = ViewWorkflow(None, "5m", 1705198187517, 1712974187517, "ZRXUSDT")
    d = workflow.get_data_g()

    CPU_CORES = multiprocessing.cpu_count() - 1 + 1
    with multiprocessing.Pool(CPU_CORES) as pool:
        tasks = [(d, i) for i in range(3, 60) ]
        results = pool.map(compute_task, tasks)
        pool.close()
        pool.join()
        print("计算结果汇总：", results)
        best_profit = 0
        best_ars = None

        for x in results:
            if x[1] > best_profit:
                best_ars = x[0]
                best_profit = x[1]
        print("best_profit={}, best_ars={}".format(best_profit, best_ars))

