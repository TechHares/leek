#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/20 20:08
# @Author  : shenglin.li
# @File    : config.py
# @Software: PyCharm
from pathlib import Path

import yaml

"""
配置信息
"""
__BASE_DIR = Path(__file__).resolve().parent.parent
__RESOURCES_DIR = __BASE_DIR.parent / 'resources'
with open(__RESOURCES_DIR / "config.yaml", "r") as f:
    cfg = yaml.safe_load(f)["leek"]


def __build_path(path):
    if path.startswith("~") or path.startswith("/"):
        return Path(path).expanduser().resolve().absolute().__str__()
    return Path(f'{__RESOURCES_DIR}/{path}').expanduser().resolve().absolute().__str__()


DATA_DIR = __build_path(cfg.get("data_dir", ""))
KLINE_DIR = __build_path(cfg.get("kline_dir", ""))
DOWNLOAD_DIR = __build_path(cfg.get("download_dir", ""))
ALERT_TYPE = cfg.get("alert_type", "")
ALERT_TOKEN = cfg.get("alert_token", "")
ALLOWED_DOMAINS = cfg.get("allowed_domains", [])

if __name__ == '__main__':
    print(Path(KLINE_DIR).expanduser().resolve().absolute())
    print(DATA_DIR)
