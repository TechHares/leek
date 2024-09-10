#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 22:09
# @Author  : shenglin.li
# @File    : strategy_arbitrage.py
# @Software: PyCharm
from datetime import datetime
import threading
from decimal import Decimal

import numpy as np
from okx import MarketData
from okx.PublicData import PublicAPI

from leek.common import EventBus, logger
from leek.common.utils import DateTime
from leek.strategy import BaseStrategy
from leek.strategy.base import Position
from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
from leek.trade.trade import PositionSide, Order, OrderType, TradeMode


class FundingStrategy(PositionRateManager, PositionDirectionManager, BaseStrategy):
    verbose_name = "资金费套利"

    def __init__(self):
        # 成本计算
        # 预期交易滑点
        # self.slippage = Decimal("0.001")
        self.slippage = Decimal("0.00")
        # 合约方向 费用
        self.short_fee = Decimal("0.003")
        self.long_fee = Decimal("0.004")
        # 单腿成交多久之后另一只腿没成交则吃单
        self.deal_timeout = 10

        # 交易配置
        # 交易工具： 1 合约+币币 2 合约+杠杆 3 合约+币币优先
        self.trade_tool = 3
        # 下单时机 分钟
        # 30 结算前30分钟 60 结算前60分钟 120 结算前120分钟
        self.max_order_time = 60
        # 下单时机
        # 30 结算前30分钟 60 结算前60分钟 120 结算前120分钟
        self.min_order_time = 15

        # 合约杠杆倍数
        self.swap_lever = 3
        # 杠杆倍数
        self.margin_lever = 3

        self.state = 0  # 0 空仓 1 已挂单 2 单腿成交 3 持仓 4 平仓挂单 5 平仓单腿成交
        self.lock = threading.RLock()

        self.funding_time = None
        self.swap_order = None
        self.swap_position = None
        self.hedging_order = None
        self.hedging_position = None

    def post_constructor(self):
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self._wrap_handle)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA_AFTER, self.order_handle)

    def handle(self):
        # todo 根据资金费收取周期不同 更细节的处理
        # todo 分仓投多标的 暂时不分
        if self.market_data.symbol != "funding":
            return
        if self.state in [1, 2, 4, 5]:
            return

        hold = None
        if self.state == 3:  # 已有持仓 判断是否可以继续持有
            holds = [funding for funding in self.market_data.rates if funding.instId == self.swap_position.symbol]
            if len(holds) == 0:  # 没找到 直接平
                self.close_funding_position()
                return
            hold = holds[0]
            rate = Decimal(hold.fundingRate)
            if self.swap_position.direction.is_long() and rate > 0:  # 费率反向 平
                self.close_funding_position()
                return
            if self.swap_position.direction.is_short() and rate < 0:  # 费率反向 平
                self.close_funding_position()
                return

        candidate_list = []
        for funding in self.market_data.rates[:10]:  # 只看前10
            profit, profit_premium, side = self._except_profit(funding)
            if profit > 0:
                candidate_list.append((funding.instId, profit, profit_premium, funding, side))
        if len(candidate_list) == 0:  # 没有可套利标的
            return
        premium_max = sorted(candidate_list, key=lambda x: x[2], reverse=True)[0]
        if self.state == 3 and hold is not None:  # 已有持仓 判断是否换仓
            rate = Decimal(hold.fundingRate)
            if premium_max[1] > abs(rate):  # 先平仓
                self.close_funding_position()
            return

        now = int(datetime.now().timestamp() * 1000)
        funding_time = int(premium_max[3].fundingTime)
        if funding_time - self.max_order_time * 60000 < now < funding_time - self.min_order_time * 60000 and \
                premium_max[1] < premium_max[2]:  # 有溢价才下单
            self.open_position(premium_max[0], premium_max[4], premium_max[3])
        if funding_time - self.min_order_time * 60000 < now < funding_time - 5 * 60000:  # 必须要下单了
            self.open_position(premium_max[0], premium_max[4], premium_max[3])

    def close_funding_position(self):
        with self.lock:
            if self.state != 3:
                return
            self.swap_order = self.swap_position.get_close_order(self._strategy_id, f"fundingclose{self._seq_id}")
            self.hedging_order = self.hedging_position.get_close_order(self._strategy_id, f"hedgingclose{self._seq_id}")
            self.bus.publish(EventBus.TOPIC_ORDER_DATA, self.swap_order)
            self.bus.publish(EventBus.TOPIC_ORDER_DATA, self.hedging_order)
            self.state = 4

    def open_position(self, symbol, side, funding_data):
        with self.lock:
            if self.state != 0:
                return
            now = datetime.now()

            # 确定对冲方式
            hedging_trade_mode = TradeMode.CROSS
            if side.is_long():  # 合约开多
                if self.trade_tool == 1:  # 合约+币币 无法对冲 不交易
                    return
            else:  # 合约开空
                if self.trade_tool in [1, 3]:  # 币币优先
                    hedging_trade_mode = TradeMode.CASH

            # 确定对冲杠杆倍数
            hedging_lever = 1 if hedging_trade_mode == TradeMode.CASH else self.margin_lever

            # 投入金额
            trade_amount = min(self.position_manager.total_amount * self.max_single_position,
                               self.position_manager.available_amount)

            # 金额分配
            trade_amount *= (hedging_lever + self.swap_lever)
            swap_amount = trade_amount * hedging_lever / (hedging_lever + self.swap_lever)
            hedging_amount = trade_amount - swap_amount

            # 计算合约下单数量
            swap_price = funding_data.swap_price
            ct_val = Decimal(funding_data.swap_instrument["ctVal"])
            num = trade_amount * self.swap_lever / (swap_price * ct_val)
            sz = num - (num % Decimal(funding_data.swap_instrument["lotSz"]))
            self._seq_id += 1
            self.swap_order = Order(strategy_id=self._strategy_id, order_id=f"funding{self._seq_id}",
                                    tp=OrderType.LimitOrder, symbol=symbol, amount=swap_amount * self.swap_lever,
                                    vol=ct_val * sz, price=swap_price, side=side, order_time=now,
                                    trade_mode=TradeMode.CROSS, sz=sz)

            # 计算下单数量
            spot_price = funding_data.spot_price
            self.hedging_order = Order(strategy_id=self._strategy_id, order_id=f"hedging{self._seq_id}",
                                       tp=OrderType.LimitOrder, symbol=symbol.replace("-SWAP", ""),
                                       amount=hedging_amount * hedging_lever,
                                       vol=ct_val * sz, price=spot_price, side=side.switch(), order_time=now,
                                       trade_mode=hedging_trade_mode)
            self.state = 1
            self.funding_time = int(funding_data.fundingTime)
            logger.info(f"套利开仓: {self.swap_order}")
            logger.info(f"套利对冲: {self.hedging_order}")
            self.bus.publish(EventBus.TOPIC_ORDER_DATA, self.swap_order)
            self.bus.publish(EventBus.TOPIC_ORDER_DATA, self.hedging_order)

    def order_handle(self, trade):
        with self.lock:
            # todo 仅单腿成交先通过滑档/市价的方式规避
            if self.state in [1, 2]:  # 开仓 / 单腿成交
                p = Position(trade.symbol, trade.side)
                amt = p.update_filled_position(trade)
                logger.info(f"套利订单回调: {trade}")
                if trade.order_id == self.swap_order.order_id:
                    if self.swap_position:
                        raise Exception(f"swap_position 已经存在{trade}, 检查交易")
                    self.swap_position = p
                elif trade.order_id == self.hedging_order.order_id:
                    if self.hedging_position:
                        raise Exception(f"hedging_position 已经存在{trade}, 检查交易")
                    self.hedging_position = p
                else:
                    logger.error(f"未知的订单信息 {trade}")
                    raise Exception(f"未知的订单信息{trade}")
                self.position_manager.available_amount -= amt
                self.state += 1
                if self.state == 3:
                    self.hedging_order = None
                    self.swap_order = None
                return

            if self.state in [4, 5]:  # 平仓挂单 / 平仓单腿成交
                if trade.order_id == self.swap_order.order_id:
                    if not self.swap_position:
                        raise Exception(f"swap_position 不存在{trade}, 检查交易")
                    amt = self.swap_position.update_filled_position(trade)
                    self.swap_position = None
                    self.swap_order = None
                elif trade.order_id == self.hedging_order.order_id:
                    if not self.hedging_position:
                        raise Exception(f"hedging_position 不存在{trade}, 检查交易")
                    amt = self.hedging_position.update_filled_position(trade)
                    self.hedging_position = None
                    self.hedging_order = None
                else:
                    logger.error(f"未知的订单信息 {trade}")
                    raise Exception(f"未知的订单信息{trade}")
                self.position_manager.available_amount += amt
                self.state += 1
                if self.state == 6:
                    self.state = 0
                return

    def _except_profit(self, funding):
        funding_rate = Decimal(funding.fundingRate)
        # 若资金费率为正，则持多仓者向持空仓者支付。
        # 若资金费率为负，则持空仓者向持多仓者支付。
        profit = abs(funding_rate) - self.short_fee - self.slippage

        # 溢价 升水贴水
        mean = np.mean(np.array(funding.swap_closes) - np.array(funding.spot_closes))
        premium = (funding.swap_price - funding.spot_price) - mean
        if funding_rate > 0:  # 做空合约
            if self.can_short():
                return profit, profit + premium, PositionSide.SHORT
        else:  # 做多
            if self.can_long():
                return profit, profit - premium, PositionSide.LONG
        return 0, 0, None


if __name__ == '__main__':
    pass
