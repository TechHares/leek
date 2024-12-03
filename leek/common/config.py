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

__default_config_file = __RESOURCES_DIR / "db-default.yaml"
__config_file = __RESOURCES_DIR / "db.yaml"
if os.path.exists(__config_file):
    with open(__config_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["leek"]
else:
    with open(__default_config_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["leek"]


def build_path(path):
    if re.match(r'^([a-zA-Z]:)|([/~])', path):
        return Path(path).expanduser().resolve().absolute().__str__()
    return Path(f'{__RESOURCES_DIR}/{path}').expanduser().resolve().absolute().__str__()

class DBConfig:
    def __init__(self, cfg):
        self.type = cfg.get("type", "sqlite").upper()
        if self.type == "SQLITE":
            self.path = build_path(cfg.get("path", "data/leek.db"))

        if self.type == "CLICKHOUSE" or self.type == "MYSQL":
            self.host = cfg.get("host")
            self.port = int(cfg.get("port"))
            self.user = cfg.get("user")
            self.password = cfg.get("password")
            self.database = cfg.get("database")
    def __str__(self):
        if self.type == "SQLITE":
            return f"{self.type}://{self.path}"
        if self.type == "CLICKHOUSE" or self.type == "MYSQL":
            return f"{self.type}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        return ""

    def to_django_db_config(self):
        if self.type == "SQLITE":
            data_dir = Path(self.path).parent.resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            return {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': Path(self.path).resolve(),
            }
        if self.type == "MYSQL":
            return {
                'ENGINE': 'django.db.backends.mysql',
                'HOST': self.host,
                'PORT': self.port,
                'USER': self.user,
                'NAME': self.database,
                'PASSWORD': self.password,
                'OPTIONS': {
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                },
            }
        if self.type == "CLICKHOUSE":
            r = {
                "ENGINE": "clickhouse_backend.backend",
                "NAME": self.database,
                "HOST": self.host,
                "USER": self.user,
                "PORT": self.port,
            }
            if self.password and self.password != "":
                r["PASSWORD"] = self.password
            return r
        return {}

    def to_client_db_config(self):
        if self.type == "SQLITE":
            data_dir = Path(self.path).parent.resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            return Path(self.path).resolve()
        if self.type == "MYSQL":
            return {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'database': self.database,
                'password': self.password,
            }
        if self.type == "CLICKHOUSE":
            args = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
            }
            if self.password and self.password != "":
                args["password"] = self.password
            return args
        return {}

# 数据库
BIZ_DB = DBConfig(cfg.get("biz_db"))  # 业务数据库
DATA_DB = DBConfig(cfg.get("data_db")) # k线数据库
if BIZ_DB.type == DATA_DB.type:
    if BIZ_DB.type == "SQLITE":
        assert BIZ_DB.path != DATA_DB.path, "业务数据库和K线数据库不能使用同一个"
    else:
        assert BIZ_DB.host != DATA_DB.host or BIZ_DB.port != DATA_DB.port or DATA_DB.database != BIZ_DB.database, "业务数据库和K线数据库不能使用同一个"

# 基础配置
DATA_DIR = build_path("data")
DOWNLOAD_DIR = build_path("download")
LOGGER_NAME = "leek"
PROXY_HOST = None
PROXY_PORT = None
PROXY = None

# 交易配置
ORDER_ALERT = False
MIN_POSITION = Decimal("0.001")
ROLLING_POSITION = True

# 告警配置
ALERT_TYPE = "console"
ALERT_TOKEN = ""

# 回测配置
BACKTEST_EMULATION = False
BACKTEST_TARGET_INTERVAL = "1m"
BACKTEST_EMULATION_INTERVAL = "5m"

# 策略设置
FILTER_RELEASE_STRATEGY = True
CLEAR_RUN_DATA_ON_ERROR = True
ALLOW_SHARE_TRADING_ACCOUNT = False
STOP_ON_ERROR = False

def set_proxy(proxy_url):
    global PROXY_HOST, PROXY_PORT, PROXY
    if not proxy_url:
        return
    PROXY = proxy_url
    arr = proxy_url.split("//")
    x = arr[0]
    if len(arr) == 2:
        x = arr[1]
    PROXY_HOST, PROXY_PORT = x.split(":")

VERSION = (0, 2, 2)
if __name__ == '__main__':
    print(BIZ_DB)
    print(PROXY_HOST)
    print(MIN_POSITION)
    print(ROLLING_POSITION)
    print(ORDER_ALERT)
