#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/16 23:06
# @Author  : shenglin.li
# @File    : unmarshal.py
# @Software: PyCharm
from decimal import Decimal


def get_dict_decimal(data, k):
    if k in data:
        return to_decimal(data[k])


def to_decimal(d):
    if d is None:
        return None
    if isinstance(d, Decimal):
        return d

    if not isinstance(d, str):
        d = str(d)

    if d == "" or d == "None" or d == "null":
        return None
    try:
        return Decimal(d)
    except BaseException:
        return None

if __name__ == '__main__':
    pass
