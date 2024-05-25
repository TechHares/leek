#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/23 20:05
# @Author  : shenglin.li
# @File    : symbol_choose.py
# @Software: PyCharm
import re
import warnings
from decimal import Decimal

import numpy as np
from joblib import Parallel, delayed

from leek.common import EventBus
from leek.common.utils import DateTime, decimal_quantize
from leek.data import BacktestDataSource
from leek.runner.backtest import BacktestWorkflow

# config
fee_type = 2
fee = Decimal("0.0005")
symbol_black_list = []

warnings.simplefilter('ignore', ResourceWarning)


def res_sort_default(results):
    results = [x for x in results if len(x[1]) > 0]
    r = sorted(results, key=lambda x: x[1][-1][1], reverse=True)[:10]
    r = [x for x in r if x[1][-1][1] > 1000]
    print([(x[0], x[1][-1][1]) for x in r])
    print(",".join([x[0] for x in r]))
    draw(r)
    return r

def draw(results):
    import plotly.graph_objs as go
    for res in results:
        symbol = res[0]
        res = res[1]
        b, s, x = zip(*res)
        symbol_rate = np.array(list(b)) / b[0]
        profit_rate = np.array(list(s)) / s[0]

        # 创建两条线的数据对象
        trace1 = go.Scatter(x=x, y=symbol_rate, mode='lines', name='base')
        trace2 = go.Scatter(x=x, y=profit_rate, mode='lines', name='profit')
        data = [trace1, trace2]
        layout = go.Layout(title=symbol, xaxis=dict(title='Time'), yaxis=dict(title='Rate'))
        fig = go.Figure(data=data, layout=layout)
        fig.show()

def get_strategy_name(cls):
    c = re.findall(r"^<(.*?) '(.*?)'>$", str(cls), re.S)[0][1]
    cls_idx = c.rindex(".")
    return c[:cls_idx] + "|" + c[cls_idx + 1:]


class SymbolChooseWorkflow:

    def __init__(self, strategy_cls, cfg_strategy, interval: str, start: str, end: str, symbols=[]):
        self.strategy_cls = strategy_cls
        cfg_strategy["strategy_cls"] = get_strategy_name(strategy_cls)
        self.cfg_strategy = cfg_strategy
        self.interval = interval
        self.start_time = DateTime.to_timestamp(start)
        self.end_time = DateTime.to_timestamp(end)
        self.symbols = symbols

    def start(self, sort_func=res_sort_default):
        symbols = self.get_all_symbol()
        prams = [(symbol, {
            "strategy_data": self.cfg_strategy,
            "trader_data": {
                "slippage": 0,
                "fee_type": fee_type,
                "fee": fee,
                "min_fee": 0,
                "limit_order_execution_rate": 100,
                "volume_limit": 4
            },
            "datasource": {
                "interval": self.interval,
                "symbols": [symbol],
                "benchmark": symbol,
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        }) for symbol in symbols]
        results = Parallel(n_jobs=-1)(delayed(self.run)(pram) for pram in prams)
        rs = sort_func(results)
        return rs

    def run(self, pram):
        x, d = pram
        workflow = BacktestWorkflow(d)
        ticket_list = []

        def set_balance(market_data):
            p = workflow.strategy.position_manager
            market_data.balance = decimal_quantize(p.available_amount + p.freeze_amount + p.position_value)
            ticket_list.append(market_data)

        workflow.bus.subscribe(EventBus.TOPIC_TICK_DATA, set_balance)
        workflow.start()
        workflow.data_source.join()
        return x, [(float(m.close), float(m.balance), DateTime.to_date_str(m.timestamp)) for m in ticket_list]

    def get_all_symbol(self):
        if len(self.symbols) > 0:
            return self.symbols
        data_source = BacktestDataSource(self.interval, [], self.start_time, self.end_time, "")
        symbols = data_source.get_all_symbol()
        return [s for s in symbols if s not in symbol_black_list]


if __name__ == '__main__':
    pass
