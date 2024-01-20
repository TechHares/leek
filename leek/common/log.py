#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 21:03
# @Author  : shenglin.li
# @File    : log.py
# @Software: PyCharm
import logging
import sys


def get_logger(name="Default", level="DEBUG", formatter="[(process)d-%(thread)d]%(levelname)s %(message)s") -> logging.Logger:
    lg = logging.getLogger(name)
    lg.setLevel(logging.getLevelName(level))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.getLevelName(level))
    handler.setFormatter(logging.Formatter(formatter))
    lg.addHandler(handler)
    return lg


logger = get_logger("Leek", "INFO", "[%(process)d-%(threadName)s] %(asctime)s [%(levelname)s]: %(message)s")

if __name__ == '__main__':
    logger.info("打印日志")
