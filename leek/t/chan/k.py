#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/15 23:26
# @Author  : shenglin.li
# @File    : k.py
# @Software: PyCharm
from abc import ABC
from ctypes import Union
from typing import List, overload

from leek.common import G
from leek.common.utils import DateTime
from leek.t.chan.comm import ChanUnion, Merger, mark_data


class ChanK(ChanUnion):
    """
    处理完相邻K包含关系之后的"禅K"
    """

    def __init__(self, k):
        super().__init__(high=k.high, low=k.low)
        self.klines = [k]  # 实际包含的k
        self.is_finish = k.finish == 1

        self.image = None

    def __copy__(self):
        target = ChanK(self.klines[0])
        if len(self.klines) == 1:
            return target
        for k in self.klines[1:]:
            target.merge(ChanK(k))
        return target

    def _merge(self, other: 'ChanUnion'):
        self.klines.extend(other.klines)

    @property
    def size(self):
        return len(self.klines)

    @property
    def start_timestamp(self):
        return self.klines[0].timestamp

    @property
    def end_timestamp(self):
        if self.next is not None:
            return self.next.start_timestamp
        if len(self.klines) > 1:
            return int(2 * self.klines[-1].timestamp - self.klines[-2].timestamp)
        return self.klines[-1].timestamp

    def mark_on_data(self):
        mark_data(self.klines[-1], "is_finish", self.is_finish)
        mark_data(self.klines[-1], "chan_high", self.high)
        mark_data(self.klines[-1], "chan_low", self.low)
        mark_data(self.klines[-1], "chan_open", self.start_value)
        mark_data(self.klines[-1], "chan_close", self.end_value)
        mark_data(self.klines[-1], "ck_idx", self.idx)

    def to_dict(self):
        assert len(self.klines) > 0
        return {
            "interval": self.klines[0].interval,
            "symbol": self.klines[0].symbol,
            "timestamp": self.klines[0].timestamp,
            "low": self.low,
            "high": self.high,
            "open": self.start_value,
            "close": self.end_value,
            "volume": sum([k.volume for k in self.klines]),
            "amount": sum([k.amount for k in self.klines])
        }

    def __str__(self):
        return (f"ChanK[{self.idx}]({DateTime.to_date_str(self.start_timestamp)}~{DateTime.to_date_str(self.end_timestamp)},"
                f" {self.size}, {self.start_value}-{self.end_value}, {"完成" if self.is_finish else "未完成"})")


class ChanKManager:
    """
    "禅K" 管理器
    """

    def __init__(self, just_included: bool = False, exclude_equal: bool = False):
        self.merger = Merger(just_included, exclude_equal)

        self.__idx = 0
        self.__chan_k_list: List[ChanK] = []

    @overload
    def __getitem__(self, index: int) -> ChanK: ...

    @overload
    def __getitem__(self, index: slice) -> List[ChanK]: ...

    def __getitem__(self, index: slice | int) -> List[ChanK] | ChanK:
        return self.__chan_k_list[index]

    def __len__(self):
        return len(self.__chan_k_list)

    def is_empty(self):
        return len(self) == 0

    def update(self, k: G) -> ChanK:
        """
        处理K线数据
        :param k: K线数据
        """
        chan_k = ChanK(k)
        self.drop_last_tmp_k()
        if not self.is_empty() and self.merger.can_merge(self[-1], chan_k):
            if not chan_k.is_finish:
                last = self[-1]
                del self.__chan_k_list[-1]
                tmp = last.__copy__()
                tmp.merge(chan_k)
                tmp.is_finish = False
                if last.is_finish:
                    tmp.image = last
                self.add_k(last)
            else:
                self[-1].merge(chan_k)
        else:
            self.add_k(chan_k)
        return self[-1]

    def drop_last_tmp_k(self):
        """
        删除最后一个未完成K线
        :return:
        """
        if not self.is_empty() and not self[-1].is_finish:
            last_image = self[-1].image
            self.__chan_k_list.pop()
            if last_image is not None:
                self.add_k(last_image)
    def add_k(self, chan_k: ChanK):
        """
        添加K线到列表
        :param chan_k: 待添加K线
        :return:
        """
        if not self.is_empty():
            self[-1].link_next(chan_k)
        if chan_k.pre is not None:
            chan_k.idx = chan_k.pre.idx + 1
        self.__chan_k_list.append(chan_k)

    def all_k_dict(self) -> List[dict]:
        return [k.to_dict() for k in self]


if __name__ == '__main__':
    pass
