#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/8 20:00
# @Author  : shenglin.li
# @File    : enums.py
# @Software: PyCharm
from enum import Enum, auto


class ChanDirection(Enum):
    """
    方向
    """
    UP = 1  # 上
    DOWN = auto()  # 下

    @property
    def is_up(self):
        return self == ChanDirection.UP

    @property
    def is_down(self):
        return self == ChanDirection.DOWN

    def reverse(self):
        return ChanDirection.UP if self.is_down else ChanDirection.DOWN


class ChanFX(Enum):
    """
    分型
    """
    TOP = 1  # 顶分型
    BOTTOM = auto()  # 底分型

    @property
    def is_top(self):
        return self == ChanFX.TOP

    @property
    def is_bottom(self):
        return self == ChanFX.BOTTOM

    @property
    def reverse(self):
        return ChanFX.TOP if self == ChanFX.BOTTOM else ChanFX.BOTTOM


class BiFXValidMethod(Enum):
    """
    bi 分型验证方法
    """
    LOSS = 0  # 宽松
    NORMAL = auto()  # 正常
    HALF = auto()  # 一般严格
    STRICT = auto()  # 严格
    TOTALLY = auto()  # 绝对严格


if __name__ == '__main__':
    pass
