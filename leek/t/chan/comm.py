#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/14 20:12
# @Author  : shenglin.li
# @File    : comm.py
# @Software: PyCharm
import abc

from leek.t.chan.enums import ChanDirection


class ChanUnion(metaclass=abc.ABCMeta):
    """
    独立缠单元， K， 特征 ...
    """

    def __init__(self, direction: ChanDirection | None = ChanDirection.UP, is_finish=False, high=None, low=None):
        """
        :param direction: 方向
        :param is_finish: 是否已经完成
        :param high: 最高价
        :param low: 最低价
        """
        self.direction = direction
        self.high = high
        self.low = low
        self.is_finish = is_finish

        self.idx = 0  # 序号
        self.pre = None  # 前一个元素
        self.next = None  # 后一个元素
        self.zs = None  # 所属中枢

    @property
    def start_origin_k(self):
        raise NotImplementedError()

    @property
    def end_origin_k(self):
        raise NotImplementedError()

    @property
    def start_value(self):
        return self.low if self.is_up else self.high

    @property
    def size(self):
        return 1

    @property
    def end_value(self):
        return self.high if self.is_up else self.low

    @property
    def is_up(self):
        return self.direction == ChanDirection.UP

    @property
    @abc.abstractmethod
    def end_timestamp(self):
        ...
    @property
    @abc.abstractmethod
    def start_timestamp(self):
        ...
    @abc.abstractmethod
    def mark_on_data(self):
        ...

    @abc.abstractmethod
    def _merge(self, other: 'ChanUnion'):
        ...

    def merge(self, other: 'ChanUnion'):
        if self.is_up:
            self.high = max(self.high, other.high)
            self.low = max(self.low, other.low)
        else:
            self.high = min(self.high, other.high)
            self.low = min(self.low, other.low)
        self._merge(other)

    def is_included(self, other: 'ChanUnion', __exclude_equal: bool = False) -> bool:
        return (not __exclude_equal and self.high >= other.high and self.low <= other.low)\
               or (self.high > other.high and self.low < other.low)

    def link_next(self, other: 'ChanUnion', update_dir: bool = True):
        """
        链接下一个
        :param update_dir:
        :param other:
        :return:
        """
        self.next = other
        other.pre = self
        if update_dir:
            other.direction = ChanDirection.UP if other.high > self.high else ChanDirection.DOWN


class Merger:
    """
    合并器
    """

    def __init__(self, just_included: bool = False, exclude_equal: bool = False):
        """
        :param just_included: 仅包含(向右包含)合并，
        :param exclude_equal: 排除相等
        """
        self.__just_included = just_included
        self.__exclude_equal = exclude_equal

    def can_merge(self, a: ChanUnion, b: ChanUnion) -> bool:
        return a.is_included(b, self.__exclude_equal) or \
               (not self.__just_included and b.is_included(a, self.__exclude_equal))


def mark_data(data, name, value):
    """
    标记数据
    :param data:
    :param name:
    :param value:
    """
    setattr(data, name, value)


if __name__ == '__main__':
    pass
