#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/28 19:30
# @Author  : shenglin.li
# @File    : decorator.py
# @Software: PyCharm
import threading


def invoke(interval=5):
    i = interval

    def decoder(func):
        def wrapper(*args, **kwargs):
            nonlocal i
            if i == interval:
                i = 0
                return func(*args, **kwargs)
            else:
                i += 1
        return wrapper
    return decoder


def locked(locker=threading.RLock()):
    def decoder(func):
        def wrapper(*args, **kwargs):
            with locker:
                return func(*args, **kwargs)
        return wrapper
    return decoder


if __name__ == '__main__':
    pass
