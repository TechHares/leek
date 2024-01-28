#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 20:56
# @Author  : shenglin.li
# @File    : worker.py
# @Software: PyCharm
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import django
from django.utils import timezone

from leek.common import logger
from leek.runner.runner import BaseWorkflow
from leek.runner.simple import SimpleWorkflow


class WorkerWorkflow(SimpleWorkflow):
    def __init__(self, cfg_data_source, cfg_strategy, cfg_trader):
        super().__init__(cfg_data_source, cfg_strategy, cfg_trader)

    def start(self):
        super()._init_config()
        self.strategy.set_dict_data(self.cfg_strategy["run_data"])
        BaseWorkflow.start(self)
        self.bus.subscribe("POSITION_DATA", self.error_wrapper(self.save_trade_log))

        try:
            while self.run_state:
                # sleep到下一个整点
                now = int(datetime.now().timestamp() / 60)  # 分钟时间戳
                time.sleep(int(60 * (5 - (now % 5))))
                self.save_run_data()
        except KeyboardInterrupt:
            pass

    def save_run_data(self):
        from .models import StrategyConfig, ProfitLog
        strategy_config = StrategyConfig.objects.get(pk=self.job_id)
        strategy_config.run_data = self.strategy.to_dict()
        logger.debug(f"更新{self.job_id}, 运行数据: {strategy_config.run_data}")
        strategy_config.just_save()

        value = self.strategy.position_value + self.strategy.available_amount + self.strategy.fee
        ProfitLog.objects.create(strategy_id=self.job_id, timestamp=int(time.time()),
                                                value=value,
                                                profit=value - self.strategy.total_amount,
                                                fee=self.strategy.fee)

    def save_trade_log(self, data):
        if data is None:
            return
        from .models import TradeLog
        TradeLog.objects.create(order_id=data.order_id, strategy_id=data.strategy_id,
                                               type=data.type.value,
                                               symbol=data.symbol, price=data.price, amount=data.amount,
                                               sz=data.sz, side=data.side.value,
                                               timestamp=timezone.make_aware(datetime.fromtimestamp(
                                                   data.order_time / 1000), timezone.get_default_timezone()),
                                               transaction_volume=data.transaction_volume,
                                               transaction_amount=data.transaction_amount,
                                               transaction_price=data.transaction_price,
                                               fee=data.fee,
                                               avg_price=self.strategy.position_map[data.symbol].avg_price,
                                               quantity=self.strategy.position_map[data.symbol].quantity)
        self.save_run_data()


def run_scheduler(*arg):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    django.setup()
    sys.path.append(f'{Path(__file__).resolve().parent.parent.parent}')

    workflow = WorkerWorkflow(*arg)
    workflow.start()
    logger.info(f"进程启动成功: {os.getpid()}")


if __name__ == '__main__':
    pass
