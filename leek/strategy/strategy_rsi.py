#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/20 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
from collections import deque
from decimal import Decimal
from typing import List

from leek.common import logger
from leek.common.utils import decimal_quantize
from leek.strategy import BaseStrategy
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager, PositionSideManager
from leek.strategy.common.strategy_filter import DynamicRiskControl, JustFinishKData
from leek.t import StochRSI
from leek.t.bias import BiasRatio
from leek.trade.trade import PositionSide


class RSIStrategy(PositionDirectionManager, PositionRateManager, DynamicRiskControl, JustFinishKData, BaseStrategy):
    verbose_name = "RSI短线择时"

    """
    RSI衡量价格变动的速度和幅度.

    参考文献：
        https://zhuanlan.zhihu.com/p/661777573
    """

    def __init__(self, period=14, over_buy=70, over_sell=30):
        self.period = int(period)
        self.over_buy = int(over_buy)
        self.over_sell = int(over_sell)
        # self.smoothing_period = int(smoothing_period)

        self.mom_window = 100
        self.mom_long_threshold = [40, 100, 70]
        self.mom_short_threshold = [0, 60, 20]

        self.ibs_rsi_threshold = [40, 60]
        self.ibs_ibs_threshold = [25, 75]

        self.rsi_func = [self.classic_rsi, self.ibs_rsi, self.mom_rsi]

    def _calculate(self):
        if self.g.q is None:
            self.g.q = deque(maxlen=max(self.period, self.mom_window))
        # 计算rsi
        data = list(self.g.q)
        cur_data = self.market_data
        if len(data) == 0:
            return
        cur_data.rsi_diff = cur_data.close - data[-1].close
        if len(data) < self.period or data[-self.period].rsi_diff is None:
            return

        if data[-1].avg_gain is None:
            gains = [max(0, d.rsi_diff) for d in data[-self.period:]]
            losses = [max(0, -d.rsi_diff) for d in data[-self.period:]]
            data[-1].avg_gain = sum(gains) / self.period
            data[-1].avg_loss = sum(losses) / self.period

        gain = max(0, cur_data.rsi_diff)
        loss = max(0, -cur_data.rsi_diff)

        cur_data.avg_gain = ((data[-1].avg_gain * (self.period - 1)) + gain) / self.period
        cur_data.avg_loss = ((data[-1].avg_loss * (self.period - 1)) + loss) / self.period
        cur_data.rsi = 100
        if cur_data.avg_loss != 0:
            cur_data.rsi = 100 - (100 / (1 + (cur_data.avg_gain / cur_data.avg_loss)))

        # 平滑RSI
        # q = [d.rs for d in data[-min(len(data), self.smoothing_period):] if d.rs is not None]
        # q.append(cur_data.rs)
        # cur_data.rsi = sum(q) / len(q)

        # 计算IBS
        cur_data.ibs = 0
        if cur_data.high != cur_data.low:
            cur_data.ibs = int((cur_data.close - cur_data.low) / (cur_data.high - cur_data.low) * 100)

        self.g.high_price = data[-1].high
        self.g.low_price = data[-1].low

    def handle(self):
        """
            三种开平仓模式
            一、经典模式: 在市场情绪处于相对低迷/高亢时入场 做反方向；RSI小于超卖超买
            二、做趋: 在市场的相对一致时入场 做同方向；RSI多头范围和多头动量条件都成立
            三、双指标: 市场表现弱/强势时入场市场出现上升/下降信号时离场

            当任一策略信号给出True值即入场做多，当所有策略信号都返回False值或达到止损目标时平仓离场
        """
        self._calculate()
        if self.market_data.finish == 1:
            self.g.q.append(self.market_data)
        if self.market_data.rsi is None:
            return
        if self.have_position():
            if all([c() for c in self.rsi_func]):
                self.close_position("RSI退出")
        else:
            print([c() == PositionSide.LONG for c in self.rsi_func])
            if self.can_long() and any([c() == PositionSide.LONG for c in self.rsi_func]):
                self.create_order(PositionSide.LONG, self.max_single_position)

            if self.can_short() and any([c() == PositionSide.SHORT for c in self.rsi_func]):
                self.create_order(PositionSide.SHORT, self.max_single_position)

    def classic_rsi(self):
        """
        1. RSI经典策略开仓
            超卖：RSI指标低于设定超卖阈值
            超买：RSI指标低于设定超买阈值
        2. 平仓
            a.突破上个bar高低点
            b.进入反向超X
        """
        if not self.have_position():
            if self.market_data.rsi < self.over_sell and self.can_long():
                return PositionSide.LONG

            if self.market_data.rsi > self.over_buy and self.can_short():
                return PositionSide.SHORT
        else:
            if self.market_data.close > self.g.high_price or self.market_data.close < self.g.low_price:
                return True

            if self.is_long_position():
                return self.market_data.rsi > self.over_buy
            else:
                return self.market_data.rsi < self.over_sell

        return None

    def mom_rsi(self):
        """
        1. RSI区域动量策略开仓
            头寸判断：使用历史(设定回看范围)rsi值计算趋势(如过去40个bar周期 rsi~[0, 60]空头, rsi~[40~100]多头)
            头寸动量：RSI的极值高/低点在N周期内大/小于阈值
            交易逻辑：
                当RSI多头范围和多头动量条件都成立时，开仓。
                当RSI多头范围和多头动量条件都不再成立时，平仓。
        """
        if not self.have_position():
            data = list(self.g.q)
            if len(data) < self.mom_window or data[-self.mom_window].rsi is None:
                return None
            data = data[-self.mom_window:]

            if self.can_long() and all(self.mom_long_threshold[0] < d.rsi < self.mom_long_threshold[1] for d in data) \
                    and any(d.rsi > self.mom_long_threshold[2] for d in data):
                return PositionSide.LONG

            if self.can_short() and all(self.mom_short_threshold[0] < d.rsi < self.mom_short_threshold[1] for d in data) \
                    and any(d.rsi < self.mom_short_threshold[2] for d in data):
                return PositionSide.SHORT
        else:
            data = list(self.g.q)[-self.mom_window:]
            if self.is_long_position():
                return not (all(
                    d.rsi is not None and self.mom_long_threshold[0] < d.rsi < self.mom_long_threshold[1] for d in data)
                            or any(d.rsi is not None and d.rsi > self.mom_long_threshold[2] for d in data))
            else:
                return not (all(
                    d.rsi is not None and self.mom_short_threshold[0] < d.rsi < self.mom_short_threshold[1] for d in
                    data)
                            or any(d.rsi is not None and d.rsi < self.mom_short_threshold[2] for d in data))
        return None

    def ibs_rsi(self):
        """
        1.RSI-IBS策略开仓
            RSI、IBS  双低开多， 双高开空
        2.平仓
            突破上个bar高低点
        """
        if not self.have_position():
            if self.can_long() and self.market_data.ibs < self.ibs_ibs_threshold[0] and self.market_data.rsi < \
                    self.ibs_rsi_threshold[0]:
                return PositionSide.LONG

            if self.can_short() and self.market_data.ibs > self.ibs_ibs_threshold[1] and self.market_data.rsi > \
                    self.ibs_rsi_threshold[1]:
                return PositionSide.SHORT
        else:
            if self.market_data.close > self.g.high_price or self.market_data.close < self.g.low_price:
                return True
            if self.is_long_position():
                return self.market_data.ibs > self.ibs_ibs_threshold[1] and self.market_data.rsi > \
                    self.ibs_rsi_threshold[1]
            else:
                return self.market_data.ibs < self.ibs_ibs_threshold[0] and self.market_data.rsi < \
                    self.ibs_rsi_threshold[0]
        return None


class RSIV2Strategy(PositionSideManager, PositionRateManager, BaseStrategy):
    verbose_name = "RSI分仓择时"

    """
    1. 分仓思路
    2. RSI确定买卖点
    3. 仓位使用预设生成， 单次开仓位控制
    4. 特定条件下(极速波动)， 平大部分仓位锁定收益
    5. 开启条件、停止条件
    6. 单方向连续开仓控制
    """

    def __init__(self, min_price=1, max_price=0, risk_rate=0.1, force_risk_rate=0.1,
                 bias_risk_rate=0.06, position_split: str = "1,1,1,1,1,1,1,1,1,1", factory=2,
                 over_buy=80, over_sell=20, window=20, limit_threshold=3, stop_condition="", start_condition=""):
        self.min_price = Decimal(min_price)
        self.max_price = Decimal(max_price)
        if self.min_price < 0 or self.max_price < 0 or self.min_price > self.max_price:
            raise RuntimeError(f"网格价格区间「{min_price}」-「{max_price}」设置不正确")
        self.risk_rate = Decimal(risk_rate)
        self.force_risk_rate = Decimal(force_risk_rate)
        self.bias_risk_rate = Decimal(bias_risk_rate)

        origin_arr = [Decimal(s.strip()) for s in position_split.split(",")]
        total_split = sum(origin_arr)
        self.position_split: List[Decimal] = [decimal_quantize(s / total_split, 2, 2) for s in origin_arr]
        self.position_split.append(Decimal(1 - sum(self.position_split)))
        logger.info(f"网格分仓比例：{self.position_split}")

        self.over_sell = int(over_sell)
        self.over_buy = int(over_buy)
        self.factory = int(factory)
        self.limit_threshold = int(limit_threshold)
        self.stop_condition = stop_condition  # 停止条件
        self.start_condition = start_condition  # 开启条件

        self.rsi = StochRSI()
        self.dq = BiasRatio(int(window))
        self.running = start_condition is None or start_condition.strip() == ""  # 是否运行
        self.bias_ratio = None
        self.k = None
        self.d = None
        self.cur_position = 0
        self.pre_is_add = False  # 上次仓位变动是否是加仓

    def data_init_params(self, market_data):
        return {
            "symbol": market_data.symbol,
            "interval": market_data.interval,
            "size": 50
        }

    def _data_init(self, market_datas: list):
        for market_data in market_datas:
            self._calculate(market_data)
        logger.info(f"RSI V2数据初始化完成")

    def _calculate(self, k):
        self.k, self.d = self.rsi.update(k)
        self.bias_ratio = self.dq.update(k)
        if self.pre_is_add:
            if (self.side.is_long and self.d > 60) or (self.side.is_short and self.d < 40):
                self.pre_is_add = False
        logger.debug(f"计算数据: k={self.k} d={self.d} pre_add={self.pre_is_add} bias_ratio={self.bias_ratio} data={k}")

    def _calc_rate(self, _to_grid) -> Decimal:
        origin_rate = None
        try:
            _to_grid = min(max(_to_grid, 0), len(self.position_split))

            # 记录超过最大结余仓位
            if self.g.remaining is None or self.cur_position == _to_grid:
                self.g.remaining = 0

            origin_rate = decimal_quantize(
                sum(self.position_split[min(self.cur_position, _to_grid): max(self.cur_position, _to_grid)]), 2, 2)
            # 减仓
            if self.cur_position > _to_grid:
                origin_rate -= (1 - Decimal(_to_grid / self.cur_position)) * self.g.remaining
                return origin_rate

            if origin_rate > self.max_single_position:
                # 记录结余
                self.g.remaining += (origin_rate - self.max_single_position)
                return self.max_single_position

            if self.g.remaining > 0:  # 使用结余填充
                closing = self.g.remaining / 4 if self.g.remaining > (
                        self.max_single_position / 10) else self.g.remaining
                origin_rate += closing
                self.g.remaining -= closing
                if origin_rate > self.max_single_position:
                    self.g.remaining += origin_rate - self.max_single_position
                    origin_rate = self.max_single_position
            return origin_rate
        finally:
            logger.debug(f"仓位计算：{self.cur_position} -> {_to_grid} 仓位比例：{origin_rate}  "
                         f"max={self.max_single_position} remaining={self.g.remaining}")

    def add_position(self):
        if not self.can(self.side):
            return
        target_gird = self._calc_grid()
        if target_gird <= self.cur_position or (self.pre_is_add and target_gird - self.cur_position < self.factory):
            logger.debug(f"无需加仓: pre_add={self.pre_is_add} | {self.factory}， "
                         f"仓位： {target_gird} / {self.cur_position}")
            return

        rate = self._calc_rate(target_gird)
        if rate <= 0:
            return
        logger.info(f"加仓：网格数{self.cur_position}/{len(self.position_split)} 目标：{target_gird} "
                    f"pre_add={self.pre_is_add} | {self.factory} 当前价格{self.market_data.close} 应持仓层数{target_gird}")
        self.g.limit = 0
        self.pre_is_add = True
        self.cur_position = target_gird
        self.create_order(self.side, rate)

    def _calc_grid(self, sub=False):
        if self.side.is_long:
            delta = self.max_price - self.market_data.close
        else:
            delta = self.market_data.close - self.min_price

        grid_deta = (self.max_price - self.min_price) / len(self.position_split)  # 单仓间距
        if sub:  # 谨慎减仓
            grid_deta += Decimal("0.5")
        target_grid = int(decimal_quantize(delta / grid_deta, 0, 1))
        return min(max(target_grid, 0), len(self.position_split))

    def sub_position(self):
        if not self.can(self.side.switch()):
            return
        target_gird = self._calc_grid(True)
        if target_gird >= self.cur_position:
            logger.debug(f"无需减仓: {target_gird} / {self.cur_position}")
            return
        rate = self._calc_rate(target_gird)
        if rate <= 0:
            return
        logger.info(f"减仓：网格数{self.cur_position}/{len(self.position_split)} 目标：{target_gird} "
                    f"当前价格{self.market_data.close} 应持仓层数{target_gird}")
        if self.g.limit is None:
            self.g.limit = 0
        self.g.limit += 1
        if self.g.limit >= self.limit_threshold and self.is_profitable():
            logger.info(f"减仓：网格数{self.cur_position}/{len(self.position_split)} 目标：{target_gird}"
                        f" 当前价格{self.market_data.close} 应持仓层数{target_gird} 连续{self.g.limit}次平仓触发止盈")
            self.close_position("止盈")
            return
        self.cur_position = target_gird
        self.close_position(rate=rate)
        # else:
        #     logger.debug(f"{self.side}方向RSI未到条件 不减仓")

    def close_position(self, memo="", extend=None, rate="1"):
        if rate == "1":
            self.cur_position = 0
        super().close_position(memo=memo, extend=extend, rate=rate)
        self.pre_is_add = False

    def can(self, side: PositionSide):
        if self.k is None or self.d is None:
            return False
        if side == PositionSide.LONG:
            return self.d < self.k < self.over_sell or self.k < 3
        else:
            return self.d > self.k > self.over_buy or self.k > 97

    def risk_control(self) -> bool:
        if not self.have_position():
            return False

        # 强制平仓
        if self.market_data.close < self.min_price * (1 - self.force_risk_rate):
            logger.error(f"多仓 价格{self.market_data.close} 低于 {self.min_price * (1 - self.force_risk_rate)} 触发强制平仓")
            self.close_position("强制平仓")
            return True
        if self.market_data.close > self.max_price * (1 + self.force_risk_rate):
            logger.error(f"空仓 价格{self.market_data.close} 高于 {self.max_price * (1 + self.force_risk_rate)} 触发强制平仓")
            self.close_position("强制平仓")
            return True

        # 风控位平仓
        if self.can(self.side.switch()):
            if self.market_data.close < self.min_price * (1 - self.risk_rate):
                logger.error(f"多仓 价格{self.market_data.close} 低于 {self.min_price * (1 - self.risk_rate)}"
                             f" k/d={self.k}/{self.d} 触发风控位平仓")
                self.close_position("风控位平仓")
                return True
            if self.market_data.close > self.max_price * (1 + self.risk_rate):
                logger.error(f"空仓 价格{self.market_data.close} 高于 {self.max_price * (1 + self.risk_rate)}"
                             f" k/d={self.k}/{self.d} 触发风控位平仓")
                self.close_position("风控位平仓")
                return True
        return False

    def is_profitable(self):
        if not self.have_position() or self.position.avg_price is None:
            return False

        return ((self.is_long_position() and self.market_data.close > self.position.avg_price)
                or (self.is_short_position() and self.market_data.close < self.position.avg_price))

    def take_profit(self) -> bool:
        # 没有仓位
        if not self.have_position() or self.bias_ratio is None or self.position.avg_price is None:
            return False
        # 乖离率不够
        if abs(self.bias_ratio) < self.bias_risk_rate:
            return False

        close = self.market_data.close
        price = self.position.avg_price
        # 亏损中或者乖离率不够
        if self.is_long_position() and (close < price or self.bias_ratio < 0):
            return False
        if self.is_short_position() and (close > price or self.bias_ratio > 0):
            return False

        logger.info(f"止盈 乖离率={self.bias_ratio} 价格={close} 开仓价格={price}")
        self.close_position("止盈")
        return True

    def running_condition(self):
        if self.running:
            if self.stop_condition == "":
                return
            if eval(self.stop_condition, {"k": self.market_data}):
                self.notify(f"触发停止条件 {self.stop_condition}")
                self.close_position("停止")
                self.running = False
        else:
            self.running = self.start_condition == "" or eval(self.start_condition, {"k": self.market_data})
            if self.start_condition != "" and self.running:
                self.notify(f"触发启动条件 {self.start_condition}")

    def handle(self):
        # 指标计算
        self._calculate(self.market_data)

        # 启停判断
        self.running_condition()
        if not self.running:
            return

        # 风控
        if self.risk_control():
            return

        # 止盈
        if self.take_profit():
            return

        # 开平仓
        price = self.market_data.close
        if price >= self.max_price or price <= self.min_price:
            logger.debug(f"价格超出网格: {self.min_price}~{self.max_price} 当前{price}")
            return

        self.add_position()
        if self.have_position():
            self.sub_position()

    def marshal(self):
        d = super().marshal()
        d["cur_position"] = "%s" % self.cur_position
        d["running"] = self.running
        g = {}
        for k in self.g_map:
            g[k] = {
                "limit": self.g_map[k].limit,
                "remaining": "%s" % self.g.remaining if self.g.remaining is not None else 0
            }
        d["g_map"] = g
        return d

    def unmarshal(self, data):
        super().unmarshal(data)
        if "running" in data:
            self.running = data["running"]
        if "cur_position" in data:
            self.cur_position = int(data["cur_position"])
        if "g_map" in data:
            for k, v in data["g_map"].items():
                self.get_g(k).limit = int(v["limit"]) if "limit" in v and v["limit"] else 0
                self.get_g(k).remaining = Decimal(v["remaining"]) if "remaining" in v and v["remaining"] else Decimal(0)


if __name__ == '__main__':
    from leek.common import G

    print(eval("k.close > 20", {
        "k": G(close=12)
    }))

    print(sum([Decimal(0.2), Decimal(6)]))
