#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/4 14:16
# @Author  : shenglin.li
# @File    : config.py
# @Software: PyCharm
import logging

from leek.common import logger, config


def load_config():
    from .models import RuntimeConfig
    if not RuntimeConfig.objects.filter(id=1).exists():
        return
    cfg = RuntimeConfig.objects.get(id=1)
    update_config(cfg)
def update_config(cfg):
    set_log_level(cfg.log_level)
    set_normal_var("DATA_DIR", config.build_path(cfg.data_dir))
    set_normal_var("DOWNLOAD_DIR", config.build_path(cfg.download_dir))
    config.set_proxy(cfg.proxy)

    set_normal_var("MIN_POSITION", cfg.min_rate)
    set_normal_var("ORDER_ALERT", cfg.order_alert)
    set_normal_var("ROLLING_POSITION", cfg.rolling_position)

    set_normal_var("ALERT_TYPE", cfg.alert_type)
    set_normal_var("ALERT_TOKEN", cfg.alert_token)

    set_normal_var("BACKTEST_EMULATION", cfg.emulation)
    set_normal_var("BACKTEST_EMULATION_INTERVAL", cfg.emulation_interval)
    set_normal_var("BACKTEST_TARGET_INTERVAL", cfg.target_interval)

    set_normal_var("FILTER_RELEASE_STRATEGY", cfg.filter_release_strategy)
    set_normal_var("CLEAR_RUN_DATA_ON_ERROR", cfg.clear_run_data_on_error)
    set_normal_var("ALLOW_SHARE_TRADING_ACCOUNT", cfg.allow_share_trading_account)
    set_normal_var("STOP_ON_ERROR", cfg.stop_on_error)

def set_log_level(level):
    if logging.getLevelName(level) != logger.level:
        logger.warning(f"更新日志等级: {level}")
        logger.setLevel(logging.getLevelName(level))

def set_normal_var(var, value):
    old_value = getattr(config, var)
    if old_value != value:
        logger.warning(f"更新{var}变量: {old_value} -> {value}")
        setattr(config, var, value)


if __name__ == '__main__':
    pass
