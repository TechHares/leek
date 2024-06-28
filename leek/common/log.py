#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 21:03
# @Author  : shenglin.li
# @File    : log.py
# @Software: PyCharm
import sys
import logging
from leek.common import notify


class ErrorFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            notify.alert(record.msg)
        return True


def get_logger(name="Default", level="DEBUG",
               formatter="[(process)d-%(thread)d]%(levelname)s %(message)s") -> logging.Logger:
    lg = logging.getLogger(name)
    lg.setLevel(logging.getLevelName(level))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.getLevelName("NOTSET"))
    handler.setFormatter(logging.Formatter(formatter))
    lg.addHandler(handler)
    lg.addFilter(ErrorFilter())
    return lg


logger = get_logger("Leek", "INFO", "[%(process)d-%(threadName)s] %(asctime)s [%(levelname)s]: %(message)s")

if __name__ == '__main__':
    logger.info("打印日志")
    logger.info("打印日志")
    logger.error("打印日志")
