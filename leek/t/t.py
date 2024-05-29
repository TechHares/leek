#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/28 19:57
# @Author  : shenglin.li
# @File    : t.py
# @Software: PyCharm
import abc
from abc import abstractmethod
from collections import deque


class T(metaclass=abc.ABCMeta):
    def __init__(self, max_cache=100):
        self.cache = deque(maxlen=max_cache)

    @abstractmethod
    def update(self, data):
        pass

    def last(self, n=100):
        n = min(len(self.cache), n)
        return list(self.cache)[-n:]


if __name__ == '__main__':
    pass
