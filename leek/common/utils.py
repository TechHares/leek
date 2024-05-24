#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 10:57
# @Author  : shenglin.li
# @File    : utils.py
# @Software: PyCharm
import importlib
import inspect
import re
import time
from collections import deque
from datetime import datetime
from decimal import *


class StateMachine(object):
    def __init__(self, state, transitions, state_size=20):
        """
        状态机初始化
        :param state: 初始化状态
        :param transitions: 转换关系 eg：{"状态1": {"事件A": "状态2", "时间B": "状态3"}}
        :param state_size: 保留状态数量
        """
        self.states = deque([state], maxlen=state_size)
        self.transitions = transitions

    def next(self, event):
        """
        :param event: 事件
        :return: 前置状态，当前状态
        """
        if self.states[-1] not in self.transitions:
            return self.states
        if event not in self.transitions[self.states[-1]]:
            return self.states
        self.states.append(self.transitions[self.states[-1]][event])
        return self.states


def decimal_quantize(d, n=2, rounding=2):
    """
    decimal 精度处理
    :param d: 待处理decimal
    :param n: 小数位数
    :param rounding: 保留方式 0 四舍五入 1 进一法 2 舍弃
    :return:
    """
    if d is None:
        return None
    r = ROUND_HALF_DOWN
    if rounding == 1:
        r = ROUND_UP
    elif rounding == 2:
        r = ROUND_DOWN

    p = "0"
    if n > 0:
        p = "0." + "0" * n
    return d.quantize(Decimal(p), rounding=r)


def decimal_to_str(obj):
    if isinstance(obj, Decimal):
        return "%s" % obj
    raise TypeError


class IdGenerator(object):
    def __init__(self, worker=1):
        self.worker = worker
        self.ts = 0
        self.idx = 0

    def next(self):
        ts = int(time.time())
        if ts != self.ts:
            self.ts = ts
            self.idx = 0
        else:
            self.idx += 1
        if self.idx > 999999:
            return self.next()
        return 1 * (10 ** 16) + self.ts * (10 ** 6) + self.idx


def get_defined_classes_in_file(file_path):
    # 导入文件中的模块
    spec = importlib.util.spec_from_file_location("module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return get_defined_classes(module.__name__)


def get_defined_classes(module_name, excludes=[], m=False):
    # 导入模块
    if m:
        module = module_name
    else:
        module = importlib.import_module(module_name)

    # 获取模块中定义的所有类
    classes = []
    for name, cls in inspect.getmembers(module, inspect.isclass):
        res = re.findall(r"^<(.*?) '(.*?)'>$", str(cls), re.S)
        if len(res) > 0 and len(res[0]) == 2 and res[0][0] == "class" and (m or res[0][1].startswith(module_name)):
            excludes_res = [res[0][1].startswith(exclude) for exclude in excludes]
            if not any(excludes_res):
                classes.append(cls)

    return classes


def get_constructor_args(cls):
    # 获取类的 __init__ 方法
    init_method = getattr(cls, "__init__")

    # 获取 __init__ 方法的参数列表
    argspec = inspect.getfullargspec(init_method)
    return argspec.args[1:]  # 忽略 self 参数


def get_all_base_classes(cls):
    base_classes = cls.__bases__
    all_base_classes = list(base_classes)
    for base_class in base_classes:
        all_base_classes.extend(get_all_base_classes(base_class))
    return all_base_classes


def get_cls(package, class_name):
    module = importlib.import_module(package)
    return getattr(module, class_name)


def all_constructor_args(cls):
    # 获取所有基类的 __init__ 方法的参数列表
    all_base_classes = get_all_base_classes(cls)
    all_args = []
    all_args.extend(get_constructor_args(cls))
    for base_class in all_base_classes:
        args = get_constructor_args(base_class)
        all_args.extend(args)
    return set(all_args)


class DateTime(object):
    PATTERN_MICROSECOND = '%Y-%m-%d %H:%M:%S.%f'
    PATTERN_SECOND = '%Y-%m-%d %H:%M:%S'
    PATTERN_MINUTE = '%Y-%m-%d %H:%M'
    PATTERN_DATE = '%Y-%m-%d'

    @staticmethod
    def to_timestamp(dt_str):
        """
        将时间转换为时间戳
        :param dt_str: 时间 字符串
        :return:
        """
        if len(dt_str) == 8:
            return int(datetime.strptime(dt_str, '%Y%m%d').timestamp() * 1000)
        if len(dt_str) == 10:
            return int(datetime.strptime(dt_str, '%Y-%m-%d').timestamp() * 1000)
        if len(dt_str) == 16:
            return int(datetime.strptime(dt_str, '%Y-%m-%d %H:%M').timestamp() * 1000)
        return int(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)

    @staticmethod
    def to_date_str(ts, pattern=PATTERN_SECOND):
        """
        将时间戳转换为时间
        :param ts: 时间戳
        :param pattern: 格式
        :return:
        """
        return datetime.fromtimestamp(ts / 1000).strftime(pattern)[:-3]


if __name__ == '__main__':
    generator = IdGenerator(1)
    for i in range(10):
        print(generator.next())
