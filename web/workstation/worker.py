#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 20:56
# @Author  : shenglin.li
# @File    : worker.py
# @Software: PyCharm
import json
import logging
import multiprocessing
import os
import queue
import sys
import time
from datetime import datetime
from pathlib import Path
from random import uniform

import django
from django.utils import timezone

from leek.common import logger, EventBus, invoke, config
from leek.runner.runner import BaseWorkflow
from leek.runner.simple import SimpleWorkflow


class WorkerWorkflow(SimpleWorkflow):
    strategy_queue_map = {}
    strategy_process_map = {}

    def __init__(self, q : multiprocessing.Queue, cfg_data_source, cfg_strategy, cfg_trader):
        super().__init__(cfg_data_source, cfg_strategy, cfg_trader)
        self.q = q

    def start(self):

        from .config import load_config, set_normal_var
        config.LOGGER_NAME = self.cfg_strategy["name"]
        load_config()
        super()._init_config()
        if "run_data" in self.cfg_strategy and len(self.cfg_strategy["run_data"]) > 0:
            try:
                self.strategy.unmarshal(self.cfg_strategy["run_data"])
            except Exception as e:
                logger.error(f"恢复数据失败：{e}")

        BaseWorkflow.start(self)
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA_AFTER, self.error_wrapper(self.save_trade_log))
        self.bus.subscribe(EventBus.TOPIC_RUNTIME_ERROR, lambda e: self.on_error())
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA_AFTER, lambda e: self.save_run_data())
        try:
            while self.run_state:
                try:
                    command = self.q.get(block=True, timeout=5)
                    logger.info(f"收到命令: {command}")
                    if command.lower() == "shutdown":
                        self.shutdown()
                    if command.lower() == "config_update":
                        time.sleep(1)
                        load_config()
                    if command.lower() == "marshal":
                        time.sleep(round(uniform(0, 3), 1))
                        self.save_run_data()
                except queue.Empty:
                    ...
        except KeyboardInterrupt:
            ...

    def save_run_data(self):
        self.update_db(run_data=self.strategy.marshal())

        # todo 暂时不做， 直接看第三方
        # value = self.strategy.position_manager.get_value()
        # ProfitLog.objects.create(strategy_id=self.job_id, timestamp=int(time.time()),
        #                          value=value,
        #                          profit=value - self.strategy.position_manager.total_amount,
        #                          fee=self.strategy.position_manager.position_value)

    def save_trade_log(self, data):
        # todo 暂时不做， 直接看第三方
        pass
        # if data is None:
        #     return
        # from .models import TradeLog
        # TradeLog.objects.create(order_id=data.order_id, strategy_id=data.strategy_id,
        #                         type=data.type.value,
        #                         symbol=data.symbol, price=data.price, amount=data.amount,
        #                         sz=data.sz, side=data.side.value,
        #                         timestamp=timezone.make_aware(datetime.fromtimestamp(
        #                             data.order_time / 1000), timezone.get_default_timezone()),
        #                         transaction_volume=data.transaction_volume,
        #                         transaction_amount=data.transaction_amount,
        #                         transaction_price=data.transaction_price,
        #                         fee=data.fee,
        #                         avg_price=self.strategy.position_map[data.symbol].avg_price,
        #                         quantity=self.strategy.position_map[data.symbol].quantity)
        # self.save_run_data()

    def update_db(self, **kwargs):
        from .models import StrategyConfig
        logger.info(f"策略数据更新{self.job_id}, {json.dumps(kwargs)}")
        StrategyConfig.objects.filter(pk=self.job_id).update(**kwargs)

    def on_error(self):
        logger.info("shutdown")
        from leek.common import config
        if config.CLEAR_RUN_DATA_ON_ERROR:
            self.update_db(run_data={})
        if config.STOP_ON_ERROR:
            self.update_db(status=1)
        self.shutdown()

    def shutdown(self):
        super().shutdown()
        logger.info("进程退出")
        os.abort()

    @staticmethod
    def send_command(command: any, strategy_id=None):
        logger.debug(f"发送命令：{strategy_id} -> {command}. {list(WorkerWorkflow.strategy_queue_map.keys())}")
        if strategy_id is None:
            for k in WorkerWorkflow.strategy_queue_map:
                WorkerWorkflow.send_command(command, k)
            return
        if strategy_id not in WorkerWorkflow.strategy_queue_map:
            return
        try:
            q = WorkerWorkflow.strategy_queue_map[strategy_id]
            q.put(command)
            logger.debug(f"命令发送完成：{strategy_id}, {command}")
        except BaseException as e:
            logger.warning(f"命令发送失败：{strategy_id}, {command}", e)

    @staticmethod
    def refresh_queue(strategy_ids):
        for k in [k for k in WorkerWorkflow.strategy_queue_map if k not in strategy_ids]:
            WorkerWorkflow.del_queue(k)

    @staticmethod
    def del_queue(strategy_id):
        logger.debug(f"删除信道：{strategy_id}")
        if strategy_id not in WorkerWorkflow.strategy_queue_map:
            return
        q = WorkerWorkflow.strategy_queue_map[strategy_id]
        pid = WorkerWorkflow.strategy_process_map[strategy_id]
        try:
            del WorkerWorkflow.strategy_queue_map[strategy_id]
            del WorkerWorkflow.strategy_process_map[strategy_id]
            q.close()
            logger.debug(f"关闭信道：{strategy_id} => {pid}")
        except BaseException as e:
            logger.warning(f"关闭信道异常：{strategy_id}", e)

    @staticmethod
    def add_queue(strategy_id, process_id, q):
        if strategy_id in WorkerWorkflow.strategy_queue_map:
            WorkerWorkflow.del_queue(strategy_id)
        WorkerWorkflow.strategy_queue_map[strategy_id] = q
        WorkerWorkflow.strategy_process_map[strategy_id] = process_id
        logger.debug(f"添加信道：{strategy_id} => {process_id}")

def run_scheduler(*arg):
    os.environ.setdefault("DISABLE_WORKER", "true")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    django.setup()
    sys.path.append(f'{Path(__file__).resolve().parent.parent.parent}')

    workflow = WorkerWorkflow(*arg)
    workflow.start()
    logger.info(f"进程启动成功: {os.getpid()}")


if __name__ == '__main__':
    pass
