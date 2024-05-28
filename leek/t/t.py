#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:57
# @Author  : shenglin.li
# @File    : t.py
# @Software: PyCharm
import abc
from abc import abstractmethod


class T(metaclass=abc.ABCMeta):
    def __init__(self, max_cache=10):
        self.max_cache = max_cache

    @abstractmethod
    def update(self, data):
        pass

    def last(self, n=10):
        pass


if __name__ == '__main__':
    pass
