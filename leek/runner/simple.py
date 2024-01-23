#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 12:07
# @Author  : shenglin.li
# @File    : simple.py
# @Software: PyCharm
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import yaml

from leek.common.event import EventBus
from leek.common.log import logger
from leek.runner.runner import BaseWorkflow
from leek.runner.notify import send_to_dingding, send_to_console

CONFIG_PATH = Path(__file__).parent.parent.parent.resolve() / 'resources/config.yaml'


class SimpleWorkflow(BaseWorkflow):
    def __init__(self, cfg_data_source, cfg_strategy, cfg_trader):
        BaseWorkflow.__init__(self, cfg_strategy["id"])
        with open(f"{CONFIG_PATH}", "r") as f:
            cfg = yaml.safe_load(f)
        self.alert_type = cfg["leek"]["alert_type"]
        self.alert_token = cfg["leek"]["alert_token"]
        self.cfg_data_source = cfg_data_source
        self.cfg_strategy = cfg_strategy
        self.cfg_trader = cfg_trader

    def _init_config(self):
        self._init_strategy(self._clean_config(self.cfg_strategy["strategy_cls"],
                                               self.cfg_strategy))
        logger.info(f"策略配置完成: {self.cfg_strategy}")
        self._init_data_source(self._clean_config(self.cfg_data_source["data_cls"],
                                                  self.cfg_data_source))
        logger.info(f"数据源配置完成: {self.cfg_data_source}")
        self._init_trader(self._clean_config(self.cfg_trader["trader_cls"],
                                             self.cfg_trader))
        logger.info(f"交易执行器配置完成: {self.cfg_trader}")

        self.bus.subscribe(EventBus.TOPIC_TICK_DATA, self.error_wrapper(self.data_source_to_strategy))
        self.bus.subscribe(EventBus.TOPIC_POSITION_DATA, self.error_wrapper(self.trader_to_strategy))
        logger.info(f"策略监听配置完成")

        self.bus.subscribe(EventBus.TOPIC_NOTIFY, self.alert)
        logger.info(f"策略通知配置完成")

    def alert(self, msg):
        logger.debug(f"通知信息：{msg}")
        if self.alert_type == "dingding":
            send_to_dingding(self.alert_token, msg)
        if self.alert_type == "console":
            send_to_console(msg)

    def error_wrapper(self, func):
        try:
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper
        except Exception as ex:
            logger.error(f"处理异常: {ex}", ex)
            self.bus.publish(EventBus.TOPIC_NOTIFY, f"处理异常: {ex}")
            self.shutdown()

    def start(self):
        self._init_config()
        super().start()


if __name__ == '__main__':
    strategy = {'id': 1, 'name': 'ETH合约网格(多)', 'total_amount': Decimal('2000.00'),
                'strategy_cls': 'leek.strategy.strategy_grid|SingleGridStrategy',
                'singlegridstrategy_symbol': 'ETH-USDT-SWAP', 'singlegridstrategy_min_price': Decimal('2000.00'),
                'singlegridstrategy_max_price': Decimal('2400.00'), 'singlegridstrategy_grid': 10,
                'singlegridstrategy_risk_rate': Decimal('0.10'), 'singlegridstrategy_direction': 1,
                'singlegridstrategy_rolling_over': 1, 'status': 3, 'process_id': 0, 'end_time': datetime(
        2024, 1, 31), 'created_time': datetime(2024, 1, 10, 8, 35, 10, 14118)}
    datasource = {'id': 1, 'name': 'OKX行情', 'data_cls': 'leek.data.data_okx|OkxKlineDataSource',
                  'okxklinedatasource_url': 'wss://ws.okx.com:8443/ws/v5/business',
                  'okxklinedatasource_channels': ['candle3m'], 'okxklinedatasource_symbols': 'ETH-USDT-SWAP',
                  'created_time': datetime(2024, 1, 10, 8, 26, 50, 533562)}
    trade = {'id': 1, 'name': 'OKX模拟交易', 'trader_cls': 'leek.trade.trade_okx|OkxTrader',
             'backtesttrader_slippage': Decimal('0.00'), 'backtesttrader_fee_type': 0,
             'backtesttrader_fee': Decimal('0.00'), 'backtesttrader_min_fee': Decimal('0.00'),
             'backtesttrader_limit_order_execution_rate': 100, 'backtesttrader_volume_limit': 4,
             'okxtrader_api_key': 'ca45455431e',
             'okxtrader_api_secret_key': '5445', 'okxtrader_passphrase': '454545',
             'okxtrader_leverage': '3', 'okxtrader_domain': 'https://www.okx.com',
             'okxtrader_ws_domain': 'wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999',
             'okxtrader_pub_domain': 'https://www.okx.com', 'okxtrader_acct_domain': 'https://www.okx.com',
             'okxtrader_flag': '0', 'okxtrader_inst_type': 'SWAP', 'okxtrader_td_mode': 'isolated',
             'created_time': datetime(2024, 1, 10, 8, 26, 13, 138334)}
    workflow = SimpleWorkflow(datasource, strategy, trade)
    workflow.start()
    print()
