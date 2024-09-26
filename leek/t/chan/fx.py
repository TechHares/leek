#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/15 20:54
# @Author  : shenglin.li
# @File    : fx.py
# @Software: PyCharm
from collections import deque
from typing import List

from leek.t.chan.comm import ChanUnion
from leek.t.chan.enums import ChanFX


class ChanFXManager:
    """
    分型
    """

    def __init__(self):
        self.__chan_list = deque(maxlen=3)

    def __getitem__(self, index: int) -> ChanUnion:
        return list(self.__chan_list)[index]

    @property
    def high(self):
        assert self.fx.is_top
        return self.point.high

    @property
    def low(self):
        assert self.fx.is_bottom
        return self.point.low

    @property
    def left(self):
        assert len(self.__chan_list) >= 1
        return self[0]

    @property
    def point(self):
        assert len(self.__chan_list) >= 2
        return self[1]

    @property
    def peak_value(self):
        assert self.fx is not None
        return self.high if self.fx.is_top else self.low

    @property
    def lst(self):
        assert len(self.__chan_list) == 3
        return list(self.__chan_list)

    @property
    def right(self):
        assert len(self.__chan_list) == 3
        return self[2]

    def next(self, k: ChanUnion) -> ChanFX:
        if len(self.__chan_list) == 0 or self[-1].idx < k.idx:
            self.__chan_list.append(k)
        else:
            self.__chan_list[-1]= k
        return self.fx

    @property
    def fx(self) -> ChanFX:
        if len(self.__chan_list) < 3:
            return None
        if self.left.high <= self.point.high and self.point.high >= self.right.high:
            return ChanFX.TOP

        if self.left.low >= self.point.low and self.point.low <= self.right.low:
            return ChanFX.BOTTOM

    @property
    def gap(self) -> bool:
        assert self.fx is not None
        return (self.fx.is_top and self.left.high < self.point.low) or (self.fx.is_bottom and self.left.low > self.point.high)

    @property
    def score(self) -> int:
        """
        分型强度打分
        :return:
        """
        # 基础一分
        score = 1

        # 三元素很直接 + 分
        if self.left.size == 1:
            score += 1
        if self.point.size == 1:
            score += 1
        if self.right.size == 1:
            score += 1
        # size = sum([self.left.size, self.point.size, self.right.size])
        # size 共4分
        # 一元素和二元素力度减弱
        if self.left.high - self.left.low < self.point.high - self.point.low:
            score += 1
        # 二元素和三素力度加强
        if self.point.high - self.point.low < self.right.high - self.right.low:
            score += 1

        # 破左元素
        if (self.fx.is_top and self.right.low < self.left.low) or (self.fx.is_bottom and self.right.high > self.left.high):
            score += 1
            # 破左元素 30% 以上
            if self.left.high - self.left.low > 0:
                if ((self.fx.is_top and (self.left.low - self.right.low) / (self.left.high - self.left.low) > 0.3 )
                        or (self.fx.is_bottom and (self.right.high - self.left.high) / (self.left.high - self.left.low) > 0.3)):
                    score += 1

        # 二三元素之间交集很少
        cross = min(self.point.high, self.right.high) - max(self.point.low, self.right.low)
        if cross < 0 or (cross / (self.point.high - self.point.low)) < 0.1: # 跳空或者10%以内
            score += 1

        if self.point.size == 1:
            from leek.t.chan.k import ChanK
            if isinstance(self.point, ChanK):
                k = self.point.klines[0]
                if (self.fx.is_top and k.close > k.open) or (self.fx.is_bottom and k.close < k.open): # 阴线
                    score += 1
                body = abs(k.open - k.close)
                if (self.fx.is_top and (k.high - k.close) > body) or (self.fx.is_bottom and (k.close - k.low) > body): # 长引线
                    score += 1

        return 1


if __name__ == '__main__':
    pass
