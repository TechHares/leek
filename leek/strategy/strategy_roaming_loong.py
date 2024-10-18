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

from leek.common import logger, G, EventBus
from leek.common.unmarshal import get_dict_decimal
from leek.common.utils import DateTime
from leek.runner.evaluation import RoamingLoongEvaluationWorkflow
from leek.runner.view import ViewWorkflow
from leek.strategy import *
from leek.strategy.common.decision import STDecisionNode, OBVDecisionNode, MADecisionNode, MACDDecisionNode, \
    VolumeDecisionNode, BollDecisionNode, MomDecisionNode, PVTDecisionNode
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.strategy.common.strategy_filter import JustFinishKData, StopLoss
from leek.t import StochRSI, MACD, MERGE, ATR
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
            if d.symbol in self._pool and self.enough_amount():  # 在操作范围 且 还有钱
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


class RoamingLoong2Strategy(PositionDirectionManager, StopLoss, PositionRateManager, JustFinishKData, BaseStrategy):
    verbose_name = "游龙二"
    """
    大周期MACD定方向 小周期StochRSI进出场 分仓增加容错率
    """

    def __init__(self, window=14, period=14, k_smoothing_factor=3, d_smoothing_factor=3, fast_period=12,
                 slow_period=26, smoothing_period=9, k_num=3, min_histogram_num=9, position_num=3, open_change_rate="0.01",
                 close_change_rate="0.01", peak_over_sell=5, over_sell=20, peak_over_buy=95, over_buy=80, threshold="0.8",
                 close_position_when_direction_change=True):
        # RSI指标
        self.window = int(window)
        self.period = int(period)
        self.k_smoothing_factor = int(k_smoothing_factor)
        self.d_smoothing_factor = int(d_smoothing_factor)
        # MACD指标
        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.smoothing_period = int(smoothing_period)
        # 方向判断
        self.k_num = int(k_num)
        self.min_histogram_num = int(min_histogram_num)

        # 开平仓条件
        self.position_num = int(position_num)  # 分仓数
        self.open_change_rate = Decimal(open_change_rate)  # 开仓价格变动比
        self.close_change_rate = Decimal(close_change_rate)  # 平仓价格变动比
        self.peak_over_sell = int(peak_over_sell)  # 极限超卖
        self.over_sell = int(over_sell)  # 超卖
        self.peak_over_buy = int(peak_over_buy)  # 极限超买
        self.over_buy = int(over_buy)  # 超买
        self.close_position_when_direction_change = str(close_position_when_direction_change).lower() in ["true", 'on', 'open', '1'] # 方向改变有仓先平
        self.abs_threshold = Decimal(threshold)

    def post_constructor(self):
        super().post_constructor()
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA_AFTER, self.handle_position)

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": max(self.window, self.period, self.k_num * (self.slow_period + self.smoothing_period + self.min_histogram_num)) + 2
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self.market_data = market_data
            self._calculate()

    def _stop_loss(self):
        if not self.have_position():
            return

        rate = self.position.avg_price / self.market_data.close if self.is_long_position() else self.market_data.close / self.position.avg_price
        rate -= 1
        if rate > self.g.open_change_rate * (self.position_num + 1):
            logger.error(f"open_change_rate止损平仓：阈值={self.g.open_change_rate * (self.position_num + 1)} "
                         f"触发价格={self.market_data.close}"
                         f" 平均持仓价={self.position.avg_price}")
            self.close_position("open_change_rate止损")
            self.g.risk = self.position_num + 1
            return True

    def _calculate(self):
        if self.g.rsi_t is None:
            self.g.rsi_t = StochRSI(window=self.window, period=self.period, k_smoothing_factor=self.k_smoothing_factor,
                                    d_smoothing_factor=self.d_smoothing_factor)

            self.g.macd_t = MACD(fast_period=self.fast_period, slow_period=self.slow_period,
                                 moving_period=self.smoothing_period, max_cache=100)
            self.g.k_merge = MERGE(window=self.k_num, max_cache=5)
            self.g.atr = ATR(window=self.window)

        k, d = self.g.rsi_t.update(self.market_data)
        self.market_data.k = k
        self.market_data.d = d

        merge_k = self.g.k_merge.update(self.market_data)
        dif, dea = self.g.macd_t.update(merge_k)
        if any([x is None for x in [k, d, dif, dea]]):
            return

        self.market_data.dif = dif
        self.market_data.dea = dea
        self.market_data.histogram = dif - dea
        self.market_data.atr = self.g.atr.update(self.market_data)
        if self.market_data.atr:
            r = self.market_data.atr / self.market_data.close * Decimal("2")
            self.g.open_change_rate = max(r * self.open_change_rate, Decimal("0.004"))
            self.g.close_change_rate = max(r * self.close_change_rate, Decimal("0.004"))


        # 定方向
        direction = None
        lst = self.g.macd_t.last(n=self.min_histogram_num + 2)
        dea_lst = [x[1] for x in lst]
        his_lst = [x[0] - x[1] for x in lst]
        if self.market_data.histogram < 0 and len([his for his in his_lst if his > 0]) >= self.min_histogram_num \
                and len([dea for dea in dea_lst if dea > 0]) >= self.min_histogram_num:  # 转空
            direction = PositionSide.SHORT if self.can_short() else None
        if self.market_data.histogram > 0 and len([his for his in his_lst if his < 0]) >= self.min_histogram_num \
                and len([dea for dea in dea_lst if dea < 0]) >= self.min_histogram_num:  # 转多
            direction = PositionSide.LONG if self.can_long() else None

        if direction:
            self.g.direction = direction
        logger.debug(f"指标计算结果: k={k}, d={d}, dif={dif}, dea={dea}, histogram={self.market_data.histogram}, price={self.market_data.close} dir={self.g.direction}")
        if self.market_data.finish != 0 and self.g.risk:
            self.g.risk -= 1

        self.market_data.direction = self.g.direction
        if self.g.last_high is not None:
            self.g.last_high = max(self.g.last_high, self.market_data.high)
        if self.g.last_low is not None:
            self.g.last_low = min(self.g.last_low, self.market_data.low)


    def handle(self):
        self._calculate()
        if self.g.direction is None or (self.g.risk is not None and self.g.risk > 0): # 方向未定， 如方向没有过度阶段， 此处不处理
            return
        if self._stop_loss():
            return

        if self.close_position_when_direction_change and self.have_position() and self.close_all_position_when_direction_change():
            return
        logger.debug(f"开平仓条件: {self.market_data.symbol}{DateTime.to_date_str(self.market_data.timestamp)} 当前方向={self.g.direction.name}"
           f" 头寸={self.position.direction.name if self.have_position() else '无'}, "
           f"over_sell={self.is_over_sell()}, over_buy={self.is_over_buy()}, p={self.g.position_num}")
        if self.is_over_sell(): # 小级别超卖
            # 需要开仓的条件：（无头寸 | 头寸为多仓位未到达上限) & 当前做多
            if self.g.direction.is_long and (not self.have_position() or self.is_long_position()):
                self.open_pos()
                return
            # 需要平仓的条件: 头寸为空
            if self.have_position() and self.is_short_position():
                self.close_pos()
                return

        if self.is_over_buy(): # 小级别超买
            # 需要开仓的条件：（无头寸 | 头寸为空仓位未到达上限) & 当前做空
            if self.g.direction.is_short and (not self.have_position() or self.is_short_position()):
                self.open_pos()
                return

            # 需要平仓的条件: 头寸为多
            if self.have_position() and self.is_long_position():
                self.close_pos()
                return

    def change_rate(self):
        if self.g.last_price is None or not self.have_position():
            return Decimal("100")

        if self.is_long_position():
            return  self.g.last_price / self.market_data.close - Decimal("1") # 为负时 处于盈利
        else:
            return  self.market_data.close / self.g.last_price  - Decimal("1") # 为负时 处于盈利

    def abs_change_rate(self):
        if not self.have_position() or self.g.last_high is None or self.g.last_low is None:
            return 0

        if self.is_long_position():
            abs_change_rate = (self.g.last_high / self.market_data.close - 1)
        else:
            abs_change_rate = (1 - self.g.last_low / self.market_data.close)
        return abs_change_rate

    def open_pos(self):
        if self.g.position_num is None:
            self.g.position_num = 0
        if not self.enough_amount():
            return

        # 仓位满了
        if self.g.position_num >= self.position_num:
            logger.debug(f"仓位已满， 放弃开仓")
            return

        change_rate = self.change_rate()
        # 变化率不够
        if change_rate < self.g.open_change_rate and (self.g.position_num > 1 or (self.g.position_num <= 1 and self.abs_change_rate() < self.abs_threshold)):
            logger.debug(f"变化率不够， 放弃开仓, cur={change_rate}")
            return

        logger.info(f"{self.market_data.symbol}加仓{self.g.position_num} -> {self.g.position_num + 1}, 上次操作价格{self.g.last_price}, 当前价格{self.market_data.close}")
        self.g.last_price = self.market_data.close
        self.g.last_high = self.market_data.high
        self.g.last_low = self.market_data.low
        self.g.position_num += 1
        rate = self.max_single_position / self.position_num
        self.create_order(side=self.g.direction, position_rate=rate, memo="开仓")


    def close_pos(self):
        if self.close_all_position_when_direction_change():  # 逆向 - 全平
            return
        change_rate = self.change_rate() * -1
        if change_rate < self.g.close_change_rate and (self.g.position_num <= 1 or self.abs_change_rate() < self.abs_threshold):
            logger.debug(f"变化率不够， 放弃减仓， cur={change_rate} pnum={self.g.position_num}, abs_rate={self.abs_change_rate()}")
            return
        assert self.g.position_num > 0, f"平仓时遇到错误仓位{self.g.position_num}"
        logger.info(f"{self.market_data.symbol}减仓{self.g.position_num} -> {self.g.position_num - 1}, 上次操作价格{self.g.last_price}, 当前价格{self.market_data.close}")
        self.g.last_price = self.market_data.close
        self.g.last_high = self.market_data.high
        self.g.last_low = self.market_data.low
        self.g.position_num -= 1
        self.close_position(memo="平仓", rate=(self.max_single_position / self.position_num) if self.g.position_num > 0 else "1")


    def close_all_position_when_direction_change(self):
        if self.position.direction != self.g.direction:  # 有持仓，且方向改变
            logger.info(f"{self.market_data.symbol}方向改变，平仓{self.position.direction}")
            self.close_position(memo=f"方向改变，平{self.position.direction}")
            return True

    def close_position(self, memo="", extend=None, rate="1"):
        if Decimal(rate) >= self.position.quantity_rate:
            self.g.position_num = 0
            self.g.last_price = None
            self.g.last_low = None
            self.g.last_high = None
        super().close_position(memo, extend, rate)

    def handle_position(self, order):
        if order.transaction_volume == 0:
            g = self.g_map[order.symbol]
            if g.position_num is not None and g.position_num > 0:
                g.position_num -= 1

    def is_over_sell(self):
        """
        超卖判断
        :return:
        """
        # 价格超卖
        # if self.g.last_price is not None and self.g.last_price / self.market_data.close - 1 > (self.open_change_rate + self.close_change_rate):
        #     return True

        # 指标超卖
        if self.market_data.k is None or self.market_data.d is None:
            return False
        return (self.market_data.d < self.market_data.k < self.over_sell
                or (self.market_data.k < self.peak_over_sell and self.market_data.d < self.peak_over_sell))


    def is_over_buy(self):
        """
        超买判断
        :return:
        """
        # 价格超买
        # if self.g.last_price is not None and self.market_data.close / self.g.last_price - 1 > (self.open_change_rate + self.close_change_rate):
        #     return True

        # 指标超买
        if self.market_data.k is None or self.market_data.d is None:
            return False
        return (self.market_data.d > self.market_data.k > self.over_buy
                or (self.market_data.k > self.peak_over_buy and self.market_data.d > self.peak_over_buy))


    def unmarshal(self, data):
        super().unmarshal(data)
        if "g" not in data:
            return
        for symbol in data["g"]:
            d = data["g"][symbol]
            g = self.get_g(symbol)
            if "direction" in d and d["direction"]:
                g.direction = PositionSide(d["direction"])
            if "position_num" in d and d["position_num"]:
                g.position_num = int(d["position_num"])
            g.last_price = get_dict_decimal(d, "last_price")
            g.last_high = get_dict_decimal(d, "last_high")
            g.last_low = get_dict_decimal(d, "last_low")

    def marshal(self):
        marshal = super().marshal()
        marshal["g"] = {}
        for symbol in self.g_map:
            g = self.g_map[symbol]
            marshal["g"][symbol] = {
                "direction": g.direction.value if g.direction else None,
                "position_num": g.position_num,
                "last_price": "%s" % g.last_price,
            }
        return marshal

if __name__ == '__main__':
    pass