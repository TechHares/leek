#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:53
# @Author  : shenglin.li
# @File    : backtest.py
# @Software: PyCharm
import json
from queue import Queue

from leek.common import EventBus
from leek.common.utils import decimal_to_str
from leek.runner.runner import BaseWorkflow, _has_override
from leek.common.evaluation import Evaluation
from leek.strategy import BaseStrategy
from leek.trade.trade import PositionSide


class BacktestWorkflow(BaseWorkflow):
    """
    回测工作流
    """
    def __init__(self, config_data):
        """
        :param config_data: 配置数据
        """
        super().__init__("T0")
        self.config_data = config_data
        self.base_line = self.config_data["datasource"]["benchmark"]
        self.base_line_init_price = None
        self.base_line_current_price = None
        self.last_report_time = None
        self.queue = Queue()
        self.idx = 1
        self.count = 0
        self.evaluation = Evaluation()
        self.long_single = 0
        self.short_single = 0
        self.trade_count = 0
        self.win_count = 0

    def start(self):
        self._init_strategy(self._clean_config(self.config_data["strategy_data"]["strategy_cls"],
                                               self.config_data["strategy_data"]))
        self._init_data_source(self._clean_config("leek.data.data_backtest|BacktestDataSource",
                                                  self.config_data["datasource"]))
        self._init_trader(self._clean_config("leek.trade.trade_backtest|BacktestTrader",
                                             self.config_data["trader_data"]))

        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.data_source_to_strategy)
        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.sync_data_to_ui)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.trader_to_strategy)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.trader_to_strategy)
        # self.bus.subscribe(EventBus.TOPIC_NOTIFY, lambda msg: print(msg))
        self.bus.subscribe("ERROR", lambda e: self.shutdown)
        self.bus.subscribe("position_update", self.position_update)

        self.bus.subscribe("backtest_data_source_done", lambda x: self.queue.put("data_source_done"))
        self.bus.subscribe("backtest_data_source_process", lambda process_num: self.queue.put({
            "type": "process",
            "data": process_num + 4
        }))
        super().start()
        self.queue.put({
            "type": "process",
            "data": 4
        })

    def position_update(self, position, order):
        if position:
            if position.direction != order.side:
                self.trade_count += 1

            if position.win:
                self.win_count += 1

    def sync_data_to_ui(self, data):
        if self.data_source.count:
            self.idx = max(self.idx, int(self.data_source.count / 2000))
        # 采集数据, 同步UI
        if data.symbol == self.base_line:
            self.base_line_current_price = data.close
            if self.base_line_init_price is None:
                self.base_line_init_price = data.close
        self.count += 1
        if self.count % self.idx != 0:
            return

        if self.last_report_time == data.timestamp:
            return
        self.last_report_time = data.timestamp
        if self.base_line_init_price:
            base_rate = (self.base_line_current_price - self.base_line_init_price) / self.base_line_init_price
        else:
            base_rate = 0

        amount = self.strategy.available_amount + self.strategy.position_value  # 当前总估值
        profit_rate = (amount - self.strategy.total_amount) / self.strategy.total_amount
        # profit_rate_execution_fee = (amount - self.strategy.total_amount) / self.strategy.total_amount
        p_data = {
            'timestamp': data.timestamp,
            'amount': amount,
            'profit_rate': profit_rate,
            # 'profit_rate_execution_fee': profit_rate_execution_fee,
            'benchmark': base_rate,
            'fee': self.strategy.fee,
            'benchmark_price': self.base_line_current_price
        }
        self.evaluation.update_profit_data(p_data)
        self.queue.put({
            "type": "profit",
            "data": json.dumps(p_data, default=decimal_to_str)
        })

    def trader_to_strategy(self, data):
        super(BacktestWorkflow, self).trader_to_strategy(data)

        if data:  # 处理交易结果
            # self.queue.put({
            #     "type": "trade",
            #     "data": json.dumps({
            #         "timestamp": data.order_time,
            #         "symbol": data.symbol,
            #         "side": data.side.value,
            #         "amount": data.amount,
            #         "price": data.price,
            #         "avg_price": decimal_quantize(position.avg_price) if position else 0,
            #         "quantity": position.quantity if position else 0,
            #     }, default=decimal_to_str)
            # })
            if data.side == PositionSide.LONG:
                self.long_single += 1
            else:
                self.short_single += 1

    def report(self):
        rp = self.queue.get()
        if rp == "data_source_done":
            self.queue.put({
                "type": "process",
                "data": 100
            })
            self.queue.put("done")
            self.shutdown()
            statistics = self.evaluation.summary_statistics()
            for k in statistics:
                if not isinstance(statistics[k], str):
                    statistics[k] = "%.4f" % statistics[k]
            statistics["trade_signal"] = "%s/%s" % (self.long_single, self.short_single)  # 交易信号(多/空)
            statistics["winning_percentage"] = (self.win_count / self.trade_count) if self.trade_count > 0 else 0  # 胜率
            statistics["average_trade_pl"] = "%.4f" % (((self.strategy.position_value + self.strategy.available_amount -
                                                        self.strategy.total_amount) / self.trade_count)
                                                       if self.trade_count > 0 else 0)  # 平均交易获利/损失
            return {
                "type": "statistics",
                "data": json.dumps(statistics, default=decimal_to_str)
            }

        return None if rp == "done" else rp


if __name__ == '__main__':
    params = {
        'strategy_data': {'csrfmiddlewaretoken': 'ptgXBn6i7eiCUdUnyfumrVkWM37DREpoeUFtDu2ZB3EBUyKIiLMMWGDY6wUGbRBc',
                          'name': 'prod', 'total_amount': '1000.00',
                          'strategy_cls': 'leek.strategy.strategy_grid|SingleGridStrategy',
                          'singlegridstrategy_symbol': 'ETHUSDT', 'singlegridstrategy_min_price': '2000.00',
                          'singlegridstrategy_max_price': '3000.00', 'singlegridstrategy_grid': '10',
                          'singlegridstrategy_risk_rate': '0.10', 'singlegridstrategy_direction': '1',
                          'singlegridstrategy_rolling_over': '1', 'actionName': 'actionValue'},
        'trader_data': {'slippage': 0, 'fee_type': '2', 'fee': 0.0005, 'min_fee': 0, 'limit_order_execution_rate': 100,
                        'volume_limit': 4},
        'datasource': {'isIndeterminateSymbols': False, 'base_line': 'ETHUSDT', 'checkAllSymbols': True,
                       'interval': '5m', 'symbols': ['BTCUSDT', 'ETHUSDT', 'TRBUSDT', 'ARBUSDT', 'DOGESDT'],
                       'daterange': [1672897865289, 1704433865289], 'start_time': 1672897865289,
                       'end_time': 1704433865289}}

    w = BacktestWorkflow(params)
    w.start()
    while x := w.report():
        pass
    print(w.evaluation.value_list)
    print(w.evaluation.benchmark_list)
    print(w.evaluation.daily)
    print(w.evaluation.fee)
