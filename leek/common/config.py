#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/20 20:08
# @Author  : shenglin.li
# @File    : config.py
# @Software: PyCharm
import os
import re
from decimal import Decimal
from pathlib import Path

import yaml

"""
配置信息
"""
__BASE_DIR = Path(__file__).resolve().parent.parent
__RESOURCES_DIR = __BASE_DIR.parent / 'resources'

__default_config_file = __RESOURCES_DIR / "config-default.yaml"
__config_file = __RESOURCES_DIR / "config.yaml"
if os.path.exists(__config_file):
    with open(__config_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["leek"]
else:
    with open(__default_config_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["leek"]


def __build_path(path):
    if re.match(r'^([a-zA-Z]:)|([/~])', path):
        return Path(path).expanduser().resolve().absolute().__str__()
    return Path(f'{__RESOURCES_DIR}/{path}').expanduser().resolve().absolute().__str__()


DATA_DIR = __build_path(cfg.get("biz_dir", ""))
DOWNLOAD_DIR = __build_path(cfg.get("download_dir", ""))
ALERT_TYPE = cfg.get("alert_type", "")
ALERT_TOKEN = cfg.get("alert_token", "")
ORDER_ALERT = bool(cfg.get("order_alert", False))
ALLOWED_DOMAINS = cfg.get("allowed_domains", [])
kline_db = cfg.get("data_db", {})
KLINE_DB_TYPE = kline_db.get("type", "sqlite").upper()
KLINE_DB_PATH = __build_path(kline_db.get("path", ""))
KLINE_DB_HOST = kline_db.get("host", "localhost")
KLINE_DB_PORT = int(kline_db.get("port", "9000"))
KLINE_DB_USER = kline_db.get("user", "default")
KLINE_DB_PASSWORD = kline_db.get("password", "")
KLINE_DB_DATABASE = kline_db.get("database", "default")
MIN_POSITION = Decimal(cfg.get("position").get("min_rate"))
ROLLING_POSITION = bool(cfg.get("position").get("rolling_position"))
BACKTEST_EMULATION = bool(cfg.get("backtest").get("emulation"))
BACKTEST_TARGET_INTERVAL = cfg.get("backtest").get("target_interval")
BACKTEST_EMULATION_INTERVAL = cfg.get("backtest").get("emulation_interval")

PROXY = cfg.get("proxy", None)
PROXY_HOST = None
PROXY_PORT = None
if PROXY:
    arr = PROXY.split("//")
    x = arr[0]
    if len(arr) == 2:
        x = arr[1]
    PROXY_HOST, PROXY_PORT = arr[1].split(":")

if BACKTEST_EMULATION and BACKTEST_TARGET_INTERVAL == BACKTEST_EMULATION_INTERVAL:
    raise Exception("target_interval and emulation_interval must be different")
if __name__ == '__main__':
    print(PROXY)
    print(PROXY_HOST)
    print(MIN_POSITION)
    print(ROLLING_POSITION)
