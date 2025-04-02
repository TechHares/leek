#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/2/26 17:40
# @Author  : shenglin.li
# @File    : dr.py
# @Software: PyCharm
from typing import List

from leek.t.chan.comm import ChanUnion, mark_data
from leek.t.chan.zs import ChanZS


class ChanDR(ChanUnion):
    """
    走势
    """

    def __init__(self, zs: ChanZS):
        """
        走势
        :param zs: 中枢
        """
        super().__init__(direction=zs.direction, high=zs.high, low=zs.low, is_finish=zs.is_finish)
        self.zs: List[ChanZS] = [zs]  # 中枢
        self.update_peak_value()

    def mark_on_data(self):
        mark_field = "dr" if self.is_finish else "dr_"
        if not self.is_finish and len(self.zs) > 1:
            if (self.is_up and self.zs[-1].end_value < self.zs[-1].down_line) or not (self.is_up and self.zs[-1].end_value > self.zs[-1].up_line):
                mark_data(self.zs[0].start_origin_k, mark_field, self.zs[0].start_value)
                mark_data(self.zs[-2].end_origin_k, mark_field, self.zs[-2].end_value)
                mark_data(self.zs[-1].end_origin_k, mark_field, self.zs[-1].end_value)
                return

        mark_data(self.zs[0].start_origin_k, mark_field, self.zs[0].start_value)
        mark_data(self.zs[-1].end_origin_k, mark_field, self.zs[-1].end_value)

    def _merge(self, other: 'ChanUnion'):
        # 不支持合并
        raise NotImplementedError()

    @property
    def start_timestamp(self):
        return self.zs[0].start_timestamp

    @property
    def size(self):
        return len(self.zs)

    @property
    def klines(self):
        lst = []
        pre_out = None
        for zs in self.zs:
            if pre_out != zs.into_ele:
                lst.extend(zs.into_ele.klines)
            for uni in zs.element_list:
                lst.extend(uni.klines)
            if zs.out_ele:
                lst.extend(zs.out_ele.klines)
                pre_out = zs.out_ele
        return lst

    @property
    def end_timestamp(self):
        return self.zs[-1].end_timestamp

    def update(self, zs: ChanZS):
        try:
            self.zs = [e for e in self.zs if not (not e.is_satisfy and e.is_finish)]
            if len(self.zs) == 0:
                self.direction = zs.direction
                self.high = zs.high
                self.low = zs.low
                self.is_finish = zs.is_finish
                self.zs: List[ChanZS] = [zs]  # 中枢
                self.update_peak_value()
                return

            if self.zs[-1].idx == zs.idx:
                return

            if zs.direction != self.direction:
                dr = ChanDR(zs)
                dr.idx = self.idx + 1
                dr.pre = self
                self.next = dr
                return dr

            self.zs.append(zs)
        finally:
            self.is_finish = len(self.zs) > 0 and all(e.is_finish and e.is_satisfy for e in self.zs)
            self.update_peak_value()

    def update_peak_value(self):
        if self.is_up:
            self.low = self.zs[0].into_ele.low
            h = [self.zs[-1].into_ele.high]
            if any(e.high for e in self.zs[-1].element_list):
                h.extend([e.high for e in self.zs[-1].element_list if e.high])
            if self.zs[-1].out_ele:
                h.append(self.zs[-1].out_ele.high)
            self.high = max(h)
        else:
            self.high = self.zs[0].into_ele.high
            l = [self.zs[-1].into_ele.low]
            if any(e.low for e in self.zs[-1].element_list):
                l.extend([e.low for e in self.zs[-1].element_list if e.low])
            if self.zs[-1].out_ele:
                l.append(self.zs[-1].out_ele.low)
            self.low = min(l)


    def __str__(self):
        return f"DR[{self.idx}](zs={self.zs})"

class ChanDRManager:
    def __init__(self):
        self.dr_list: List[ChanDR] = []

    def update(self, chan: ChanZS):
        if chan is None:
            return
        if len(self.dr_list) == 0:
            self.dr_list.append(ChanDR(chan))
            return
        new_dr = self.dr_list[-1].update(chan)
        if new_dr is not None:
            self.dr_list.append(new_dr)

if __name__ == '__main__':
    pass
