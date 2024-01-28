#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/20 20:08
# @Author  : shenglin.li
# @File    : config.py
# @Software: PyCharm
import re
from pathlib import Path

import yaml

"""
配置信息
"""
__BASE_DIR = Path(__file__).resolve().parent.parent
__RESOURCES_DIR = __BASE_DIR.parent / 'resources'
with open(__RESOURCES_DIR / "config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)["leek"]


def __build_path(path):
    if re.match(r'^([a-zA-Z]:)|([/~])', path):
        return Path(path).expanduser().resolve().absolute().__str__()
    return Path(f'{__RESOURCES_DIR}/{path}').expanduser().resolve().absolute().__str__()


DATA_DIR = __build_path(cfg.get("biz_dir", ""))
DOWNLOAD_DIR = __build_path(cfg.get("download_dir", ""))
ALERT_TYPE = cfg.get("alert_type", "")
ALERT_TOKEN = cfg.get("alert_token", "")
ALLOWED_DOMAINS = cfg.get("allowed_domains", [])
kline_db = cfg.get("data_db", {})
KLINE_DB_TYPE = kline_db.get("type", "sqlite").upper()
KLINE_DB_PATH = __build_path(kline_db.get("path", ""))
KLINE_DB_HOST = kline_db.get("host", "localhost")
KLINE_DB_PORT = int(kline_db.get("port", "9000"))
KLINE_DB_USER = kline_db.get("user", "default")
KLINE_DB_PASSWORD = kline_db.get("password", "")
KLINE_DB_DATABASE = kline_db.get("database", "default")

if __name__ == '__main__':
    print(DATA_DIR)
