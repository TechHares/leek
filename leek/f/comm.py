#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/12 19:20
# @Author  : shenglin.li
# @File    : comm.py
# @Software: PyCharm
import abc
import re
from collections import deque
from io import UnsupportedOperation

from leek.common import G


class Expression(abc.ABC):
    """
    表达式定义
    """

    @abc.abstractmethod
    def next(self, k: G):
        ...

    def __add__(self, other):
        return Ops.ops(self, other, "+")

    def __radd__(self, other):
        return Ops.ops(other, self, "+")

    def __sub__(self, other):
        return Ops.ops(self, other, "-")

    def __rsub__(self, other):
        return Ops.ops(other, self, "-")

    def __mul__(self, other):
        return Ops.ops(self, other, "*")

    def __rmul__(self, other):
        return Ops.ops(other, self, "*")

    def __div__(self, other):
        return Ops.ops(self, other, "/")

    def __rdiv__(self, other):
        return Ops.ops(other, self, "/")

    def __truediv__(self, other):
        return self.__div__(other)

    def __rtruediv__(self, other):
        return self.__rdiv__(other)

    def __call__(self, *args, **kwargs):
        return self.next(k=args[0])

    def __gt__(self, other):
        return Ops.ops(self, other, ">")

    def __ge__(self, other):
        return Ops.ops(self, other, ">=")

    def __lt__(self, other):
        return Ops.ops(self, other, "<")

    def __le__(self, other):
        return Ops.ops(self, other, "<=")
    def __eq__(self, other):
        return Ops.ops(self, other, "==")

    def __ne__(self, other):
        return Ops.ops(self, other, "!=")

    def get_real_value(self, exp, k: G):
        if exp is None:
            return None
        if isinstance(exp, Expression):
            return self.get_real_value(exp.next(k), k)
        return exp

    def need_cache(self, k):
        return not hasattr(k, "finish") or k.finish is None or k.finish == 1


class Ops(Expression):
    @staticmethod
    def ops(left, right, ops):
        o = Ops()
        o.left = left
        o.right = right
        o.ops = ops
        return o

    def __init__(self):
        self.ops = None
        self.left = None
        self.right = None

    def next(self, k: G):
        if self.left is None or self.right is None:
            return None

        left_value = self.get_real_value(self.left, k)
        if left_value is None:
            return None
        right_value = self.get_real_value(self.right, k)
        if right_value is None:
            return None

        if self.ops == "-":
            return left_value - right_value
        if self.ops == "+":
            return left_value + right_value
        if self.ops == "*":
            return left_value * right_value
        if self.ops == "/":
            return left_value / right_value
        if self.ops == ">":
            return left_value > right_value
        if self.ops == ">=":
            return left_value >= right_value
        if self.ops == "<":
            return left_value < right_value
        if self.ops == "<=":
            return left_value <= right_value
        if self.ops == "==":
            return left_value == right_value
        if self.ops == "!=":
            return left_value != right_value
        raise UnsupportedOperation(f"UnsupportedOperation {self.ops}")

    def __str__(self):
        return f"({self.left} {self.ops} {self.right})"


class RollingExpression(Expression, metaclass=abc.ABCMeta):
    def __init__(self, n):
        super().__init__()
        self.n = n
        self.cache = deque(maxlen=n-1)

    @abc.abstractmethod
    def calculate(self, k: G):
        ...

    def next(self, k: G):
        cache, value = self.calculate(k)
        if cache is not None and self.need_cache(k):
            self.cache.append(cache)
        return value

    def is_full(self):
        return len(self.cache) == self.n - 1


class FullRollingExpression(RollingExpression, metaclass=abc.ABCMeta):
    def __init__(self, v_func, n):
        super().__init__(n)
        self.v_func = v_func

    def calculate(self, k: G):
        cache_value = self.get_real_value(self.v_func, k)
        res = self._calculate(list(self.cache) + [cache_value]) if self.is_full() else None
        return cache_value, res

    @abc.abstractmethod
    def _calculate(self, lst):
        ...

class Expressions:
    """
    表达式工具
    """
    exps = {}

    @staticmethod
    def register(name, func):
        Expressions.exps[name] = func

    @staticmethod
    def parse_expression(elp):
        # Following patterns will be matched:
        # - $close -> value("close")
        # - $open+$close -> value("open")+value("close")
        if not isinstance(elp, str):
            elp = str(elp)
        chinese_punctuation_regex = r"\u3001\uff1a\uff08\uff09"
        for pattern, new in [
            (rf"\$([\w{chinese_punctuation_regex}]+)", r'value("\1")'),
        ]:  # Value  # Expressions
            elp = re.sub(pattern, new, elp)

        return eval(elp, Expressions.exps)


if __name__ == '__main__':
    field = Expressions.parse_expression("ref($close, 2)/ref($close, 1) - 1")
    print(field)
