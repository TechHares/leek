#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 11:21
# @Author  : shenglin.li
# @File    : base.py
# @Software: PyCharm
import decimal
import inspect
import signal
from importlib import import_module

from leek.common import EventBus, logger
from leek.data.data import DataSource, WSDataSource
from leek.strategy import BaseStrategy
from leek.trade.trade import Trader


def _init_model(ins_cfg):
    module = import_module(ins_cfg["package"])

    cls = getattr(module, ins_cfg["class"])
    sig = inspect.signature(cls)
    params = sig.parameters
    parameter_map = {k: v for k, v in ins_cfg["config"].items() if k in list(params.keys())}
    return cls(**parameter_map)


class BaseWorkflow(object):
    """
    流定义基类
    """
    def __init__(self, job_id):
        self.data_source: DataSource = None
        self.trader: Trader = None
        self.strategy: BaseStrategy = None

        self.job_id = job_id
        self.bus: EventBus = EventBus()
        self.run_state = True

    def start(self):
        signal.signal(signal.SIGTERM, lambda signal, frame: self.shutdown())
        self.data_source.start()

    def _clean_config(self, cls, cfg):
        arr = cls.split("|")
        pkg = arr[0].strip(" ")
        cls = arr[1].strip(" ")
        pre = cls.lower() + "_"
        rd = {
            "package": pkg,
            "class": cls
        }
        rcfg = {}
        for k, v in cfg.items():
            if pre in k:
                rcfg[k.replace(pre, "")] = v
            else:
                rcfg[k] = v
        rd["config"] = rcfg
        return rd

    def _init_trader(self, cfg_trader):
        instance = _init_model(cfg_trader)
        if isinstance(instance, Trader):
            Trader.__init__(instance, self.bus)
        self.trader = instance

    def _init_strategy(self, cfg_strategy):
        instance = _init_model(cfg_strategy)
        if isinstance(instance, BaseStrategy):
            available_amount = None
            used_amount = None
            if "available_amount" in cfg_strategy["config"]:
                available_amount = cfg_strategy["config"]["available_amount"]
            if "used_amount" in cfg_strategy["config"]:
                used_amount = cfg_strategy["config"]["used_amount"]
            BaseStrategy.__init__(instance, self.job_id, self.bus,
                                  decimal.Decimal(cfg_strategy["config"]["total_amount"]),
                                  available_amount, used_amount)
        self.strategy = instance

    def _init_data_source(self, cfg_data_source):
        instance = _init_model(cfg_data_source)
        if isinstance(instance, DataSource):
            DataSource.__init__(instance, self.bus)
        if isinstance(instance, WSDataSource):
            if "url" not in cfg_data_source["config"]:
                raise RuntimeError("WSDataSource 需配置「url」属性")
            WSDataSource.__init__(instance, cfg_data_source["config"]["url"])
        self.data_source = instance

    def strategy_to_trader(self, data):
        if data:
            order = self.trader.order(data)
            self.trader_to_strategy(order)

    def data_source_to_strategy(self, data):
        BaseStrategy.handle(self.strategy, data)
        order = self.strategy.handle(data)
        self.strategy_to_trader(order)

    def trader_to_strategy(self, data):
        if data:
            BaseStrategy.handle_position(self.strategy, data)
            self.strategy.handle_position(data)

    def shutdown(self):
        logger.info(f"{self.strategy.job_id} 收到停止信号！")
        self.run_state = False
        self.data_source.shutdown()
        self.strategy.shutdown()
        self.trader.shutdown()
        logger.info(f"{self.strategy.job_id} 停止成功！")


if __name__ == '__main__':
    pass
