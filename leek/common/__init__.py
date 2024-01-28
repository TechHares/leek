#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 18:05
# @Author  : shenglin.li
# @File    : __init__.py.py
# @Software: PyCharm
"""
公共工具包
"""

from leek.common.log import logger, get_logger
from leek.common.event import EventBus
from leek.common import config
from leek.common.utils import IdGenerator


class G(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        kwargs = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return str(kwargs)


__all__ = ["EventBus", "logger", "get_logger", "config", "G", "IdGenerator"]

if __name__ == '__main__':
    pass
