#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 15:53
# @Author  : shenglin.li
# @File    : backtest.py
# @Software: PyCharm
import json
from queue import Queue

import numpy as np

from leek.common import EventBus
from leek.common.utils import decimal_to_str
from leek.runner.runner import BaseWorkflow, _has_override
from leek.strategy import BaseStrategy
from leek.trade.trade import PositionSide


class Evaluation(object):
    def __init__(self):
        """
        策略评价
        自评：
        1.年化收益率
        2.累计收益率
        3.波动率
        4.夏普比率
        5.日度收益率
        6.最大回撤
        7.sortino比率
        8.下行风险
        9.最大回撤期内收益
        10.资本回报率
        11.信息比率
        12.负载率
        13.alpha
        14.beta
        15.R平方
        16.Treynor比率
        17.Calmar比率
        """
        self.value_list = []
        self.benchmark_list = []
        self.daily = 0
        self.fee = 0

        self.benchmark_arr = None
        self.value_arr = None

    def __getattribute__(self, name):
        def _get(_attr):
            return object.__getattribute__(self, _attr)

        def _set(_attr, v):
            return object.__setattr__(self, _attr, v)

        if name == "update_profit_data":
            if _get("value_arr") is not None:
                _set("value_arr", None)
                _set("benchmark_arr", None)
        elif name.startswith("calculate_"):
            if _get("value_arr") is None:
                _set("value_arr", np.array(_get("value_list")))
            if _get("benchmark_arr") is None:
                _set("benchmark_arr", np.array(_get("benchmark_list")))
            if len(_get("value_list")) == 0:
                def no_data(*args, **kwargs):
                    return "--"

                return no_data
        return _get(name)

    def update_profit_data(self, data):
        if "amount" not in data or not data["amount"] or data["amount"] <= 0:
            return

        if "benchmark_price" not in data or not data["benchmark_price"] or data["benchmark_price"] <= 0:
            return

        d = int(data["timestamp"] / (1000 * 60 * 60 * 24))
        if d < self.daily:
            return
        if d == self.daily:
            self.value_list[-1] = float(data["amount"])
            self.benchmark_list[-1] = float(data["benchmark_price"])
        else:
            self.value_list.append(float(data["amount"]))
            self.benchmark_list.append(float(data["benchmark_price"]))
            self.daily = d
        self.fee = float(data["fee"])

    def calculate_annualized_return(self, day_in_year=360):
        """
        :return: 年化收益率
        """
        return self.calculate_average_daily_return() * day_in_year

    def calculate_cumulative_return(self):
        """
        :return: 累计收益率
        """
        return (self.value_list[-1] - self.value_list[0]) / self.value_list[0]

    def calculate_volatility(self):
        """
        :return: 波动率
        """
        return np.std(np.diff(self.value_arr) / self.value_arr[:-1])

    def calculate_sharpe_ratio(self, risk_free_rate=0.03/365):
        """
        :return: 夏普比率
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        std = np.std(daily_returns)
        if std == 0:
            return 0
        return (np.mean(daily_returns) - risk_free_rate) / std

    def calculate_average_daily_return(self):
        """
        :return: 日度收益率
        """
        return np.mean(np.diff(self.value_arr) / self.value_arr[:-1])

    def calculate_max_drawdown(self):
        """
        :return: 最大回撤
        """
        # 计算每个时间点之前的峰值
        peak_values = np.maximum.accumulate(self.value_arr)
        # 计算每个时间点的回撤
        drawdowns = (self.value_arr - peak_values) / peak_values
        # 找到最大回撤
        return np.min(drawdowns)

    def calculate_sortino_ratio(self, risk_free_rate=0.03/365):
        """
        :return: sortino比率
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1] - risk_free_rate
        # 提取负收益
        negative_returns = daily_returns[daily_returns < 0]
        std = np.std(negative_returns)
        if std == 0:
            return 0
        return (self.calculate_average_daily_return() - risk_free_rate) / std

    def calculate_downside_risk(self, risk_free_rate=0.03/365):
        """
        :return: 下行风险
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1] - risk_free_rate
        # 提取负收益
        negative_returns = daily_returns[daily_returns < 0]
        negative_returns_squared_sum = np.sum(negative_returns ** 2)

        # 计算观测期数
        n = len(self.value_arr)

        # 计算负收益的标准差，即下行风险
        return np.sqrt(negative_returns_squared_sum / n)

    def calculate_max_drawdown_return(self):
        """
        :return: 最大回撤期内收益
        """
        # 计算每个时间点之前的峰值
        peak_values = np.maximum.accumulate(self.value_arr)

        # 计算每个时间点的回撤
        drawdowns = (self.value_arr - peak_values) / peak_values
        # 找到最大回撤的开始和结束位置
        start_index = np.argmax(drawdowns == 0)  # 最大回撤开始位置
        end_index = np.argmax(drawdowns == np.min(drawdowns))  # 最大回撤结束位置
        # 计算最大回撤期间收益
        return (self.value_arr[end_index] - self.value_arr[start_index]) / self.value_arr[start_index]

    def calculate_capital_return(self):
        """
        :return: 资本回报率
        """
        return (self.value_list[-1] - self.value_list[0] - self.fee) / self.value_list[0]

    def calculate_information_ratio(self):
        """
        :return: 信息比率
        """
        # 计算每日收益
        portfolio_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        benchmark_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算每日超额收益
        excess_returns = portfolio_returns - benchmark_returns
        # 计算超额收益的平均值和标准差
        mean_excess_returns = np.mean(excess_returns)
        std_excess_returns = np.std(excess_returns)
        # 计算信息比率
        return mean_excess_returns / std_excess_returns if std_excess_returns != 0 else 0

    def calculate_beta(self):
        """
        :return: 负载率
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        if len(asset_returns) < 2:
            return 0
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算资产与市场的协方差矩阵
        covariance_matrix = np.cov(asset_returns, market_returns)
        # 提取资产与市场的协方差和市场的方差
        covariance_asset_market = covariance_matrix[0, 1]
        variance_market = covariance_matrix[1, 1]

        # 计算Beta
        return covariance_asset_market / variance_market

    def calculate_alpha(self, risk_free_rate=0.03/365):
        """
        :return: alpha
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算Alpha
        expected_market_return = risk_free_rate + self.calculate_beta() * (np.mean(market_returns) - risk_free_rate)
        actual_asset_return = np.mean(asset_returns)
        return actual_asset_return - expected_market_return

    def calculate_r_squared(self):
        """
        :return: R平方
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算残差平方和 rss
        residual_sum_of_squares = np.sum((asset_returns - market_returns) ** 2)

        # 计算总平方和
        total_sum_of_squares = np.sum((asset_returns - np.mean(asset_returns)) ** 2)

        # 计算R平方
        if total_sum_of_squares == 0:
            return 0
        return 1 - (residual_sum_of_squares / total_sum_of_squares)

    def calculate_treynor_ratio(self, risk_free_rate=0.03/365):
        """
        :return: Treynor比率
        """
        # 假设有资产（或投资组合）和市场的每日收益率数据
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        # 计算超额收益
        excess_returns = asset_returns - risk_free_rate
        # 计算Treynor比率
        beta = self.calculate_beta()
        if beta == 0:
            return 0
        return np.mean(excess_returns) / beta

    def calculate_calmar_ratio(self, day_in_year=360):
        """
        :return: Calmar比率
        """
        try:
            return self.calculate_annualized_return(day_in_year) / self.calculate_max_drawdown()
        except Exception:
            return 0

    def summary_statistics(self):
        if len(self.value_list) == 0:
            return {}
        return {
                "annualized_return": "%.2f%%" % (self.calculate_annualized_return() * 100),  # 年化收益率
                "cumulative_return": "%.2f%%" % (self.calculate_cumulative_return() * 100),  # 累计收益率
                "sharpe_ratio": self.calculate_sharpe_ratio(),  # 夏普比率
                "average_daily_return": "%.2f%%" % (self.calculate_average_daily_return() * 100),  # 日均收益率
                "volatility": self.calculate_volatility(),  # 波动率
                "maximum_drawdown": "%.2f%%" % (self.calculate_max_drawdown() * 100),  # 最大回撤
                "downside_risk": self.calculate_downside_risk(),  # 下行风险
                "sortino_ratio": self.calculate_sortino_ratio(),  # Sortino比率
                "maximum_drawdown_duration": "%.2f%%" % (self.calculate_max_drawdown_return() * 100),  # 最大回撤期内收益
                "capital_utilization": "%.2f%%" % (self.calculate_capital_return() * 100),  # 资本回报率
                "calmar_ratio": self.calculate_calmar_ratio(),  # calmar比率
                "alpha": self.calculate_alpha(),  # Alpha
                "beta": self.calculate_alpha(),  # Beta
                "r_squared": self.calculate_r_squared(),  # R-squared
                "information_ratio": self.calculate_information_ratio(),  # 信息比率
                "treynor_ratio": self.calculate_treynor_ratio(),  # Treynor比率
            }


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

        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.sync_data_to_ui)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.trader_to_strategy)
        # self.bus.subscribe(EventBus.TOPIC_NOTIFY, lambda msg: print(msg))
        self.bus.subscribe("ERROR", lambda e: self.shutdown)
        self.bus.subscribe(EventBus.TOPIC_POSITION_UPDATE, self.position_update)

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

    def position_update(self, position, trade):
        if position:
            if position.direction != trade.side:
                self.trade_count += 1

            if (position.direction != trade.side) \
                    and (
                    (position.direction == PositionSide.LONG and trade.transaction_price > position.avg_price)
                    or
                    (position.direction == PositionSide.SHORT and trade.transaction_price < position.avg_price)
            ):
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

        amount = self.strategy.position_manager.available_amount + self.strategy.position_manager.position_value  # 当前总估值
        profit_rate = (amount - self.strategy.position_manager.total_amount) / self.strategy.position_manager.total_amount
        # profit_rate_execution_fee = (amount - self.strategy.total_amount) / self.strategy.total_amount
        p_data = {
            'timestamp': data.timestamp,
            'amount': amount,
            'profit_rate': profit_rate,
            # 'profit_rate_execution_fee': profit_rate_execution_fee,
            'benchmark': base_rate,
            'fee': self.strategy.position_manager.fee,
            'benchmark_price': self.base_line_current_price
        }
        self.evaluation.update_profit_data(p_data)
        self.queue.put({
            "type": "profit",
            "data": json.dumps(p_data, default=decimal_to_str)
        })

    def trader_to_strategy(self, data):
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
            statistics["average_trade_pl"] = "%.4f" % (((self.strategy.position_manager.position_value +
                                                         self.strategy.position_manager.available_amount -
                                                        self.strategy.position_manager.total_amount) / self.trade_count)
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
