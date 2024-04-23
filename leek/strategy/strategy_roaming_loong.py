#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/16 18:53
# @Author  : shenglin.li
# @File    : strategy_roaming_loong.py
# @Software: PyCharm
import copy
import datetime
import threading
from abc import abstractmethod, ABCMeta
from collections import deque
from decimal import Decimal
from itertools import product
from threading import Thread

import numpy as np

from leek.common import logger, G
from leek.runner.evaluation import RoamingLoongEvaluationWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy import *
from leek.strategy.common.decision import STDecisionNode, OBVDecisionNode, MADecisionNode, MACDDecisionNode, \
    VolumeDecisionNode, BollDecisionNode, MomDecisionNode, PVTDecisionNode
from leek.strategy.common.strategy_common import PositionRateManager
from leek.trade.trade import PositionSide


class AbcRoamingLoongStrategy(PositionRateManager, BaseStrategy, metaclass=ABCMeta):
    verbose_name = "游龙"
    """
    增加操作标的池子，间隔固定周期后刷新操作标的池
    """

    def __init__(self):
        pool_num = "10"
        volatility_threshold = "0.005"
        computed_length = "4320"
        refresh_period = "1440"
        loss_rate = "0.0005"
        expected_trade_count = "12"
        """
        :param pool_num: 标的池大小
        :param volatility_threshold: 入池波动率阈值
        :param computed_length: 计算数据长度
        :param refresh_period: 刷新周期
        :param loss_rate: 计算损失率
        :param expected_trade_count: 一个周期内期望的最佳交易数据
        """

        self._pool_num = int(pool_num)
        self._volatility_threshold = float(volatility_threshold)
        self._computed_length = int(computed_length)
        self._refresh_period = int(refresh_period)
        self._loss_rate = Decimal(loss_rate)
        self._expected_trade_count = int(expected_trade_count)

        self._pool: dict[str, float] = {}
        self.__computed_data: dict[str, G] = {}
        self._lock = threading.RLock()

    def handle(self):
        d = self.market_data
        if d.symbol not in self.__computed_data:
            self.__computed_data[d.symbol] = G(
                next_refresh_counter=self._computed_length,
                data_queue=deque(maxlen=self._computed_length),
                status="collect"
            )
        # 计算指标
        g = self.__computed_data[d.symbol]
        g.data_queue.append(d)
        data = list(g.data_queue)
        self.computed(data)

        if self.have_position():  # 已有持仓
            self.close_handle(data)
        else:  # 未持有
            if d.symbol in self._pool:  # 在操作范围
                self.open_handle(data)
        with self._lock:
            g.next_refresh_counter -= 1
        if g.next_refresh_counter == 0:
            if self.test_mode:
                self._refresh_pool(data, g)
            else:
                threading.Thread(target=self._refresh_pool, args=(data, g), daemon=True).start()

    def _refresh_pool(self, data, g):
        g.status = "eval"
        try:
            std = np.array([x.close for x in data]).std()
            volatility = std / data[-1].close
            logger.info(f"评估：{data[-1].symbol} volatility={volatility} / {self._volatility_threshold}")
            if volatility < self._volatility_threshold:
                if data[0].symbol in self._pool:
                    del self._pool[data[0].symbol]
                return
            g.eval = RoamingLoongEvaluationWorkflow(self._loss_rate)
            for i in range(1, len(data)):
                g.price = data[i].close
                if not g.eval.have_position():
                    self.open_handle(data[:i])
                else:
                    self.close_handle(data[:i])
                g.eval.handle_data(data[i].close)

            trade_count, profit, draw_downs = g.eval.get_eval_data()
            logger.info(f"评估：{data[-1].symbol} trade_count={trade_count} profit={profit} draw_downs={draw_downs}")
            if profit <= 1:
                if data[0].symbol in self._pool:
                    del self._pool[data[0].symbol]
                return
            score1 = 1 / (1 + abs(trade_count - self._expected_trade_count) ** 2 / (trade_count + 1))
            score2 = profit - 1
            score3 = -draw_downs
            score = Decimal(score1) * 2 + score2 * 5 + score3 * 3
            with self._lock:
                if data[0].symbol in self._pool:
                    self._pool[data[0].symbol] = score
                    return

                min_symbol = min(self._pool, key=lambda k: self._pool[k]) if len(self._pool) > 0 else None
                if min_symbol is None or score > self._pool[min_symbol]:
                    self._pool[data[0].symbol] = score

                if len(self._pool) > self._pool_num:
                    del self._pool[min_symbol]
        finally:
            with self._lock:
                g.next_refresh_counter = self._refresh_period
            g.status = "collect"

    def create_order(self, side: PositionSide, position_rate="0.5", memo="", extend=None):
        g = self.__computed_data[self.market_data.symbol]
        if g.status == "eval":
            g.eval.trade(side, g.price)
            return
        return super().create_order(side, position_rate, memo, extend)

    def close_position(self, memo="", extend=None):
        g = self.__computed_data[self.market_data.symbol]
        if g.status == "eval":
            g.eval.close_trade(g.price)
            return
        return super().close_position(memo, extend)

    @abstractmethod
    def computed(self, data) -> G:
        pass

    @abstractmethod
    def open_handle(self, data):
        pass

    @abstractmethod
    def close_handle(self, data):
        pass


class RoamingLoong1Strategy(AbcRoamingLoongStrategy):
    verbose_name = "游龙一"
    """
    组合SMIIO 和 ST 的决策，周期刷新操作标的池作为后一段时间操作标的选择
    """

    def __init__(self):
        self.period = 10
        self.factory = 3

        self.fast_period = 17
        self.slow_period = 34
        self.sigma_period = 9

    def _computed_st(self, data):
        d = data[-1]
        if len(data) < 2:
            d.st_tr = d.high - d.low
            return

        d.st_tr = max(d.high - d.low, abs(d.high - data[-2].close), abs(d.low - data[-2].close))
        if len(data) < self.period:
            return
        d.st_atr = sum([d.st_tr for d in data[-self.period:]]) / self.period
        # basic 可以选择 sma/close/avg(high+low)/avg_price 此处选close
        basic = d.close
        d.st_up = basic + self.factory * d.st_atr
        d.st_low = basic - self.factory * d.st_atr

        if data[-2].st_up is None or data[-2].st_low is None:
            d.st_trend = basic
            return

        if basic > data[-2].st_trend:
            d.st_trend = max(d.st_low, data[-2].st_trend)
        else:
            d.st_trend = min(d.st_up, data[-2].st_trend)

    def _computed_mom(self, data):
        if len(data) < 2:
            data[-1].smiio_diff = 0
            data[-1].smiio_fast_pc = 0
            data[-1].smiio_fast_pc_abs = 0
            data[-1].smiio_slow_pc = 0
            data[-1].smiio_slow_pc_abs = 0
            data[-1].smiio_erg = 0
            data[-1].smiio_sig = 0
            data[-1].smiio_osc = 0
            return

        # data[-1].smiio_diff = (data[-1].amount / data[-1].volume - data[-2].amount / data[-2].volume) * data[-1].volume
        try:
            data[-1].smiio_diff = data[-1].amount / data[-1].volume - data[-2].amount / data[-2].volume
        except Exception:
            data[-1].smiio_diff = 0
        slow_alpha = Decimal(2 / (self.slow_period + 1))
        fast_alpha = Decimal(2 / (self.fast_period + 1))
        data[-1].smiio_slow_pc = slow_alpha * data[-1].smiio_diff + (1 - slow_alpha) * data[-2].smiio_slow_pc
        data[-1].smiio_fast_pc = fast_alpha * data[-1].smiio_slow_pc + (1 - fast_alpha) * data[-2].smiio_fast_pc

        data[-1].smiio_slow_pc_abs = abs(slow_alpha * data[-1].smiio_diff) + (1 - slow_alpha) * data[-2].smiio_slow_pc_abs
        data[-1].smiio_fast_pc_abs = abs(fast_alpha * data[-1].smiio_slow_pc_abs) + (1 - fast_alpha) * data[-2].smiio_fast_pc_abs

        # Indicator
        data[-1].smiio_erg = 0 if data[-1].smiio_fast_pc == 0 else data[-1].smiio_fast_pc / data[-1].smiio_fast_pc_abs
        # Signal
        tsi_alpha = Decimal(2 / (self.sigma_period + 1))
        data[-1].smiio_sig = tsi_alpha * data[-1].smiio_erg + (1 - tsi_alpha) * data[-2].smiio_erg
        # Oscillator
        data[-1].smiio_osc = data[-1].smiio_erg - data[-1].smiio_sig

    def _computed_volatility(self, data):
        std = np.array([x.close for x in data]).std()
        volatility = std/data[-1].close
        data[-1].volatility = volatility
        if len(data) == 1:
            data[-1].volatility_sig = volatility
            data[-1].volatility_osc = 0
            return
        alpha = Decimal(2 / (self.sigma_period + 1))
        data[-1].volatility_sig = alpha * volatility + (1 - alpha) * data[-2].volatility
        data[-1].volatility_osc = volatility - data[-1].volatility_sig

    def computed(self, data):
        self._computed_mom(data)
        self._computed_st(data)
        # self._computed_volatility(data)

    def open_handle(self, data):
        cur = data[-1]
        if cur.st_trend is None:
            return
        if len(data) < 5:
            return
        if all([x.smiio_erg > 0.5 for x in data[-5:]]):
            return
        if cur.smiio_erg < data[-2].smiio_erg or cur.smiio_erg < data[-3].smiio_erg:
            return
        # if cur.volatility < cur.volatility_sig or not cur.volatility_osc > data[-2].volatility_osc > data[-3].volatility_osc:
        #     return

        if cur.smiio_erg < cur.smiio_sig or not cur.smiio_sig > data[-2].smiio_sig > data[-3].smiio_sig:
            return
        if cur.smiio_erg > 0 and cur.smiio_osc > 0 and cur.st_trend < cur.close:
            self.create_order(PositionSide.LONG, self.max_single_position)

    def close_handle(self, data):
        cur = data[-1]
        if cur.st_trend > cur.close:
            self.close_position()


if __name__ == '__main__':
    pass
