#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/12 19:20
# @Author  : shenglin.li
# @File    : comm.py
# @Software: PyCharm
import re


def value(k):
    return k.close

def ref(v, n: int = 0):
    while n < 0:
        v = v.pre
        n += 1
    return v

def parse_expression(elp):
    # Following patterns will be matched:
    # - $close -> value("close")
    # - $open+$close -> value("open")+value("close")
    if not isinstance(elp, str):
        elp = str(elp)
    chinese_punctuation_regex = r"\u3001\uff1a\uff08\uff09"
    for pattern, new in [
        (rf"\$([\w{chinese_punctuation_regex}]+)", r'value("\1")'),
        (r"(\w+\s*)\(", r"ELP.\1("),
    ]:  # Value  # Expressions
        elp = re.sub(pattern, new, elp)
    return elp

if __name__ == '__main__':
    field = parse_expression("ref($close, -2)/ref($$close, -1) - 1")
    print(field)
