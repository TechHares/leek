#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/9 20:42
# @Author  : shenglin.li
# @File    : strategy_voting.py
# @Software: PyCharm
import copy
import datetime
import threading
from collections import deque
from decimal import Decimal
from itertools import product
from threading import Thread

from leek.common import logger
from leek.runner.view import ViewWorkflow
from leek.strategy import *
from leek.strategy.common.decision import STDecisionNode, OBVDecisionNode, MADecisionNode, MACDDecisionNode, \
    VolumeDecisionNode, BollDecisionNode, MomDecisionNode, PVTDecisionNode
from leek.strategy.common.strategy_common import PositionRateManager
from leek.trade.trade import PositionSide


class DecisionStrategy(PositionRateManager, BaseStrategy):
    verbose_name = "多数决策略"
    """
    多个技术指标同时决策，一段周期后根据胜率/平均回报率决定下一周期投票权重
    """

    def __init__(self):

        # 决策节点超参数
        self.decision_node_params = {
            OBVDecisionNode: {"fast_period": range(3, 15), "slow_period": range(15, 40, 2)},
            # MADecisionNode: {"fast_period": range(3, 15), "slow_period": range(15, 40, 3)},
            # MACDDecisionNode: {"fast_period": range(3, 15, 2), "slow_period": range(15, 40, 3),
            #                    "moving_period": range(5, 12)},
            # STDecisionNode: {"period": range(10, 26, 2), "factory": range(1, 5)},
            # VolumeDecisionNode: {"fast_period": range(3, 15, 2), "slow_period": range(15, 40, 3)},
            # BollDecisionNode: {"period": range(7, 30, 2), "num_std_devs": range(2, 10)},
            # MomDecisionNode: {"period": (7, 30, 3), "price_type": range(1, 8)},
            # PVTDecisionNode: {"fast_period": range(3, 15), "slow_period": range(15, 40, 3)}
        }
        self.evaluation_data_length = 12 * 24 * 7  # 评估数据容器数据量
        self.re_eval_internal = self.evaluation_data_length / 7  # 重新评估周期
        self.evaluation_fee_rate = Decimal(0.0005)  # 手续费率

    def pre_handle(self):
        if self.g.lock is None:
            self.g.lock = threading.RLock()
        with self.g.lock:
            # 决策节点评估数据容器
            if self.g.evaluation_data is None:
                self.g.next_eval_counter = self.evaluation_data_length
                self.g.evaluation_data = deque(maxlen=self.evaluation_data_length)
            self.g.evaluation_data.append(self.market_data)
            # 重新评估计数器
            self.g.next_eval_counter -= 1
            counter = self.g.next_eval_counter
            # 决策权重
            if self.g.weight_params is None:
                self.g.weight_params = {}
                for decision_cls in self.decision_node_params.keys():
                    self.g.weight_params[decision_cls] = 1 / len(self.decision_node_params)
            # 开仓阈值
            if self.g.threshold is None:
                self.g.threshold = Decimal(0.8)

            # 决策实例容器
            if self.g.decision_node_instance is None:
                self.g.decision_node_instance = {}
                for decision_cls in self.decision_node_params.keys():
                    self.g.decision_node_instance[decision_cls] = decision_cls()

        # if counter == 0:
            # if self.test_mode:
            #     self.re_eval_decision()
            # else:
            #     threading.Thread(target=self.re_eval_decision, daemon=True).start()

    def computed_vote_value(self, vote_func):
        """
        计算投票价值
        :return:
        """
        vote_value = 0
        # 投票权重
        weight_params = self.g.weight_params
        # 决策实例容器
        for cls in self.g.decision_node_instance:
            ins = self.g.decision_node_instance[cls]
            if vote_func(ins):
                vote_value += weight_params[cls]
        return vote_value

    def handle(self):
        self.pre_handle()
        if self.have_position():
            value = self.computed_vote_value(lambda ins: ins.close_long(self.market_data))
            if value >= self.g.threshold:
                self.close_position()

        else:
            if not self.enough_amount():
                return

            value = self.computed_vote_value(lambda ins: ins.open_long(self.market_data))
            if value >= self.g.threshold:
                self.create_order(PositionSide.LONG, self.max_single_position)

    def re_eval_decision(self):
        logger.info("标的%s开始重新评估决策节点参数及权重", self.market_data.symbol)
        evaluation_data = copy.copy(self.g.evaluation_data)
        ins_map = {}  # 实例容器
        best_profit_map = {}  # 最佳参数下的收益 -> 权重
        for cls in self.decision_node_params:
            best_args, best_profit = self.best_args(evaluation_data, cls, **self.decision_node_params[cls])
            ins_map[cls] = cls(**best_args)
            best_profit_map[cls] = float(best_profit)
        profit_sum = sum(best_profit_map.values())
        profit_avg = profit_sum / len(best_profit_map)
        shift = 0
        if profit_min := min(best_profit_map.values()) < 0:
            shift = -profit_min * 1.5
            profit_sum = (profit_sum + shift) * len(best_profit_map)

        for cls in best_profit_map:
            profit = best_profit_map[cls]
            best_profit_map[cls] = (profit + shift) / profit_sum
        with self.g.lock:
            # 阈值刷新
            self.g.threshold = 0.5 + max((0.5 - max(10 * profit_avg, 0)), 0)
            self.g.next_eval_counter = self.re_eval_internal
            self.g.weight_params = best_profit_map
        logger.info("标的%s重新评估决策节点参数及权重完成, 阈值:%s, 权重:%s, 计数器:%s",
                    self.market_data.symbol, self.g.threshold, self.g.weight_params, self.g.next_eval_counter)

    def best_args(self, evaluation_data, decision_cls, **kwargs):
        keys = kwargs.keys()
        values = [kwargs[key] for key in keys]
        combinations = list(product(*values))
        avg_profit = -1
        best_args = {}
        best_trade_count = 0
        best_profit = 0
        for combination in combinations:
            eval_args = dict(zip(keys, combination))
            decision = decision_cls(**eval_args)
            trade_count, profit = decision.evaluation(copy.deepcopy(evaluation_data), self.evaluation_fee_rate)
            if trade_count == 0:
                continue
            avg = (profit - 1) / trade_count
            if avg > avg_profit:
                avg_profit = avg
                best_args = eval_args
                best_trade_count = trade_count
                best_profit = profit
                print("decision_cls:{}, trade_count={}, avg_profit:{}, args={}".format(decision_cls.__name__,
                                                                                       trade_count, profit, eval_args))
        logger.info("decision_cls:{}, best_trade_count:{}, best_profit:{}, args={}"
                    .format(decision_cls.__name__, best_trade_count, best_profit - 1, best_args))
        return best_args, best_profit - 1


if __name__ == '__main__':
    # workflow = ViewWorkflow(None, "5m", 1710000000000, 1710604800000, "ZRXUSDT")
    # workflow = ViewWorkflow(None, "5m", 1675180800000, 1676390400000, "ZRXUSDT")
    workflow = ViewWorkflow(None, "5m", 1707926400000, 1711641600000, "ZRXUSDT")
    data = workflow.get_data_g()

    strategy = DecisionStrategy()
    now = datetime.datetime.now()
    strategy.best_args(data, OBVDecisionNode, fast_period=range(3, 15), slow_period=range(15, 40))
    # best_trade_count:36, best_profit:2.578177995573759019278577644, args={'fast_period': 13, 'slow_period': 23}
    # strategy.best_args(MADecisionNode, fast_period=range(3, 15), slow_period=range(15, 40, 2))
    # best_trade_count:51, best_profit:1.805003968763135809955039614, args={'fast_period': 10, 'slow_period': 21}
    # strategy.best_args(MACDDecisionNode, fast_period=range(3, 15), slow_period=range(15, 40, 3), moving_period=range(5, 12))
    # best_trade_count:31, best_profit:1.732646252645825297275368249, args={'fast_period': 13, 'slow_period': 39, 'moving_period': 11}
    # strategy.best_args(STDecisionNode, period=range(10, 26), factory=range(1, 5), price_type=range(1, 8))
    # best_trade_count:1, best_profit:2.193019566367001586462189318, args={'period': 7, 'factory': 6}
    # strategy.best_args(VolumeDecisionNode, fast_period=range(3, 15), slow_period=range(15, 40, 2))
    # best_trade_count:41, best_profit:1.623165768439564445737300344, args={'fast_period': 13, 'slow_period': 39}
    # strategy.best_args(BollDecisionNode, period=range(7, 30), num_std_devs=range(2, 10))
    # best_trade_count:275, best_profit:2.543715503998371631671431165, args={'period': 14, 'num_std_devs': 3}
    # strategy.best_args(MomDecisionNode, period=(7, 30), price_type=range(1, 8))
    # best_trade_count: 68, best_profit: 1.704232968333797373311481129, args = {'period': 30, 'price_type': 3}
    # strategy.best_args(PVTDecisionNode, fast_period=range(3, 15), slow_period=range(15, 40, 2))
    # best_trade_count:36, best_profit:2.709314152418426290980838816, args={'fast_period': 13, 'slow_period': 23}
    print("cost:{}".format((datetime.datetime.now() - now).seconds))
