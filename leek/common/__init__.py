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
from leek.common.utils import IdGenerator, StateMachine
from leek.common.decorator import locked, invoke


class G(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        kwargs = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return str(kwargs)

    def __getattribute__(self, name):
        if name.startswith('__'):
            return object.__getattribute__(self, name)
        items = self.__dict__
        if name not in items:
            object.__setattr__(self, name, None)
        return object.__getattribute__(self, name)

    def get(self, name):
        items = self.__dict__
        if name not in items:
            return None
        return object.__getattribute__(self, name)

    def __json__(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def __copy__(self):
        return self.__class__(**self.__json__())



__all__ = ["EventBus", "logger", "get_logger", "config", "G", "IdGenerator", "StateMachine", "locked", "invoke"]

if __name__ == '__main__':
    g = G()
    print(g.r)
    g.r = 1
    print(g.r)
