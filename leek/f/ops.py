#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/9/14 19:18
# @Author  : shenglin.li
# @File    : ops.py
# @Software: PyCharm
import math
import statistics
from collections import deque
from typing import Dict

import numpy as np
from scipy.stats import rankdata

from leek.common import G
from leek.f.comm import Expression, Expressions, RollingExpression, FullRollingExpression
from sklearn.metrics import r2_score


class Ref(RollingExpression):
    """
    向前找N步
    """

    def __init__(self, func, prev_n=1):
        assert prev_n > 0, "Ref prev_n must > 0"
        super().__init__(prev_n + 1)
        self.func = func

    def calculate(self, k: G):
        value = self.get_real_value(self.func, k)
        r = None
        if len(self.cache) >= self.n - 1:
            r = self.cache[-self.n + 1]
        return value, r

    def __str__(self):
        return f"ref({self.func}, {self.n - 1})"


class Value(Expression):
    """
    取值
    """

    def __init__(self, filed_name):
        super().__init__()
        self.filed_name = filed_name

    def next(self, k: G):
        if "vwap" == self.filed_name:
            return float(k.amount / k.volume) if k.volume > 0 else float(k.close)
        return float(getattr(k, self.filed_name))

    def __str__(self):
        return f"${self.filed_name}"


class Larger(Expression):
    """
    取大值
    """

    def __init__(self, *args):
        super().__init__()
        self.args = args

    def next(self, k: G):
        max_value = None
        for arg in self.args:
            arg_value = self.get_real_value(arg, k)
            if arg_value is None:
                continue
            if max_value is None or arg_value > max_value:
                max_value = arg_value
        return max_value

    def __str__(self):
        return f"larger({','.join(map(str, self.args))})"


class Smaller(Expression):
    """
    取小值
    """

    def __init__(self, *args):
        super().__init__()
        self.args = args

    def next(self, k: G):
        min_value = None
        for arg in self.args:
            arg_value = self.get_real_value(arg, k)
            if arg_value is None:
                continue
            if min_value is None or arg_value < min_value:
                min_value = arg_value
        return min_value

    def __str__(self):
        return f"smaller({','.join(map(str, self.args))})"


class Abs(Expression):
    """
    绝对值
    """

    def __init__(self, v):
        super().__init__()
        self.args = v

    def next(self, k: G):
        value = self.get_real_value(self.args, k)
        if value is None:
            return None
        return abs(value)

    def __str__(self):
        return f"abs({self.args})"


class Sma(FullRollingExpression):
    """
    简单移动平均
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return sum(lst) / self.n

    def __str__(self):
        return f"sma({self.v_func}, {self.n})"


class Std(FullRollingExpression):
    """
    标准差
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return statistics.pstdev(lst)

    def __str__(self):
        return f"std({self.v_func}, {self.n})"


class Max(RollingExpression):
    """
    最大值
    """

    def __init__(self, v, n):
        super().__init__(n)
        self.v = v

    def calculate(self, k: G):
        value = self.get_real_value(self.v, k)
        return value, max(list(self.cache) + [value])

    def __str__(self):
        return f"max({self.v}, {self.n})"


class Min(RollingExpression):
    """
    最小值
    """

    def __init__(self, v, n):
        super().__init__(n)
        self.v = v

    def calculate(self, k: G):
        value = self.get_real_value(self.v, k)
        return value, min(list(self.cache) + [value])

    def __str__(self):
        return f"min({self.v}, {self.n})"


class Slope(FullRollingExpression):
    """
    斜率
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return np.polyfit(range(1, len(lst) + 1), np.array(lst), 1)[0]

    def __str__(self):
        return f"slope({self.v_func}, {self.n})"


class R2(FullRollingExpression):
    """
    R-squared
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        x = np.array(range(1, len(lst) + 1))
        y = np.array(lst)
        # 拟合线性模型
        coeffs = np.polyfit(x, y, 1)
        p = np.poly1d(coeffs)
        # 计算拟合值
        yhat = p(x)
        # 计算R-squared
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        if ss_tot == 0:
            return 1
        return 1 - (ss_res / ss_tot)

    def __str__(self):
        return f"r2({self.v_func}, {self.n})"


class Resi(FullRollingExpression):
    """
    拟合残差
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        x = np.array(range(1, len(lst) + 1))
        y = np.array(lst)
        # 拟合线性模型
        coeffs = np.polyfit(x, y, 1)
        p = np.poly1d(coeffs)
        # 计算拟合值
        yhat = p(x)
        return (y - yhat)[-1]

    def __str__(self):
        return f"resi({self.v_func}, {self.n})"


class Quantile(FullRollingExpression):
    """
    X分位
    """

    def __init__(self, v, n, q):
        assert 0 < q < 1
        super().__init__(v, n)
        self.q = q

    def _calculate(self, lst):
        return np.quantile(lst, self.q)

    def __str__(self):
        return f"quantile({self.v_func}, {self.n}, {self.q})"


class Rank(FullRollingExpression):
    """
    排名 百分位
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return rankdata(lst, method="min")[-1] / self.n

    def __str__(self):
        return f"rank({self.v_func}, {self.n})"


class IdxMax(FullRollingExpression):
    """
    最大值索引 取值范围 [0, n)
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        v = lst[0]
        idx = 0
        for i in range(len(lst)):
            if lst[i] >= v:
                v = lst[i]
                idx = i
        return idx

    def __str__(self):
        return f"idxmax({self.v_func}, {self.n})"


class IdxMin(FullRollingExpression):
    """
    最小值索引 取值范围 [0, n)
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        v = lst[0]
        idx = 0
        for i in range(len(lst)):
            if lst[i] <= v:
                v = lst[i]
                idx = i
        return idx

    def __str__(self):
        return f"idxmin({self.v_func}, {self.n})"


class Log(Expression):
    """
    求对数
    """

    def __init__(self, v):
        super().__init__()
        self.v = v

    def next(self, k: G):
        value = self.get_real_value(self.v, k)
        if value is None:
            return None
        return math.log(value)

    def __str__(self):
        return f"log({self.v})"


class Corr(RollingExpression):
    """
    相关性计算
    """

    def __init__(self, y_func, x_func, n):
        super().__init__(n)
        self.y_func = y_func
        self.x_func = x_func

    def calculate(self, k: G):
        y = self.get_real_value(self.y_func, k)
        x = self.get_real_value(self.x_func, k)

        res = self._calculate(x, y) if self.is_full() else None
        return (x, y) if x is not None and y is not None else None, res

    def _calculate(self, x, y):
        x_ = [e[0] for e in list(self.cache)] + [x]
        y_ = [e[1] for e in list(self.cache)] + [y]
        if all([v == y for v in y_]):
            return 0
        return np.corrcoef(x_, y_)[0, 1]

    def __str__(self):
        return f"corr({self.y_func}, {self.x_func}, {self.n})"


class Count(FullRollingExpression):
    """
    统计条件为真的个数
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return sum(1 for x in lst if x)

    def __str__(self):
        return f"count({self.v_func}, {self.n})"


class Sum(FullRollingExpression):
    """
    求和
    """

    def __init__(self, v, n):
        super().__init__(v, n)

    def _calculate(self, lst):
        return sum(lst)

    def __str__(self):
        return f"sum({self.v_func}, {self.n})"


class IfZero(Expression):
    def __init__(self, v, default):
        super().__init__()
        self.v = v
        self.default = default

    def next(self, k: G):
        value = self.get_real_value(self.v, k)
        return value if value != 0 else self.default


Expressions.register("ref", Ref)
Expressions.register("value", Value)
Expressions.register("larger", Larger)
Expressions.register("ifzero", IfZero)
Expressions.register("smaller", Smaller)
Expressions.register("abs", Abs)
Expressions.register("sma", Sma)
Expressions.register("std", Std)
Expressions.register("min", Min)
Expressions.register("max", Max)
Expressions.register("log", Log)
Expressions.register("count", Count)
Expressions.register("sum", Sum)

Expressions.register("slope", Slope)
Expressions.register("r2", R2)
Expressions.register("resi", Resi)
Expressions.register("corr", Corr)

Expressions.register("quantile", Quantile)
Expressions.register("rank", Rank)
Expressions.register("idxmax", IdxMax)
Expressions.register("idxmin", IdxMin)


class Processor:
    """
    执行过程封装
    """

    def __init__(self, name, exp):
        self.name = name
        self.exp = exp
        self.elp = Expressions.parse_expression(exp)

    def next(self, k: G):
        elp = self.elp(k)
        setattr(k, self.name, elp)
        return elp

    @staticmethod
    def wrapper_processor(ft_dict: Dict[str, str]):
        processors = []
        for k in ft_dict:
            processors.append(Processor(k, ft_dict[k]))

        def _wrapper(k_line):
            for p in processors:
                p.next(k_line)

        return _wrapper


if __name__ == '__main__':
    ...
