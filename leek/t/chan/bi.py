#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/16 21:33
# @Author  : shenglin.li
# @File    : bi.py
# @Software: PyCharm
from typing import List, overload

from scipy.constants import value

from leek.common import G
from leek.common.utils import DateTime
from leek.t.chan.comm import ChanUnion, mark_data
from leek.t.chan.enums import ChanDirection, BiFXValidMethod
from leek.t.chan.fx import ChanFXManager
from leek.t.chan.k import ChanK, ChanKManager


class ChanBI(ChanUnion):
    """
    笔
    """

    def __init__(self, chan_k_list: List[ChanK], is_finish=False, direction: ChanDirection = ChanDirection.UP):
        assert direction is not None
        super().__init__(direction=direction, is_finish=is_finish)

        self.chan_k_list: List[ChanK] = chan_k_list
        assert len(self.chan_k_list) > 2
        self.update_peak_value()

    @property
    def k_idx(self):
        return [k.idx for k in self.chan_k_list]

    @property
    def size(self):
        if self.is_finish or self.next is not None:
            return len(self.chan_k_list) - 2

        return len(self.chan_k_list) - 1

    @property
    def start_origin_k(self):
        for k in self.chan_k_list[1].klines:
            if self.direction.is_up and k.low == self.start_value:
                return k
            if self.direction.is_down and k.high == self.start_value:
                return k

    @property
    def end_origin_k(self):
        for k in self.chan_k_list[-2].klines:
            if self.direction.is_up and k.high == self.end_value:
                return k
            if self.direction.is_down and k.low == self.end_value:
                return k

    @property
    def start_timestamp(self):
        return self.chan_k_list[1].start_timestamp

    @property
    def end_timestamp(self):
        return self.chan_k_list[-1].start_timestamp

    def update_peak_value(self):
        if self.is_up:
            self.low = self.chan_k_list[1].low
            self.high = max([k.high for k in self.chan_k_list[-2:]])
        else:
            self.high = self.chan_k_list[1].high
            self.low = min([k.low for k in self.chan_k_list[-2:]])
        # assert self.high > self.low

    def _merge(self, other: 'ChanBI'):
        for idx in range(len(other.chan_k_list)):
            if self.chan_k_list[-1].idx < other.chan_k_list[idx].idx:
                self.chan_k_list.extend(other.chan_k_list[idx:])
                break
        self.update_peak_value()

    def mark_on_data(self):
        mark_field = "bi" if self.is_finish else "bi_"
        mark_data(self.start_origin_k, mark_field, self.start_value)
        mark_data(self.end_origin_k, mark_field, self.end_value)
        mk = self.get_middle_k()
        mark_data(mk, "bi_value", (self.start_value + self.end_value) / 2)
        mark_data(mk, "bi_idx", self.idx)

    def get_middle_k(self):
        target_k_num = sum([len(k.klines) for k in self.chan_k_list]) // 2
        for k in self.chan_k_list:
            if len(k.klines) > target_k_num:
                return k.klines[0]
            target_k_num -= len(k.klines)
            continue

    def get_k_by_ts(self, ts):
        if self.start_timestamp > ts or self.end_timestamp < ts:
            return None
        for k in self.chan_k_list:
            if k.start_timestamp <= ts <= k.end_timestamp:
                return k.klines[0]
        return None

    def add_chan_k(self, chan_k: ChanK):
        if self.chan_k_list[-1].idx < chan_k.idx:
            self.chan_k_list.append(chan_k)
        else:
            self.chan_k_list[-1] = chan_k
        if self.pre is not None and len(self.chan_k_list) > 5:  # 尝试提前结束前笔
            if ((self.is_up and max([x.high for x in self.chan_k_list[:3]]) < min(
                    [x.low for x in self.chan_k_list[-2:]]))
                    or (not self.is_up and min([x.low for x in self.chan_k_list[:3]]) < max(
                        [x.high for x in self.chan_k_list[-2:]]))):
                self.pre.is_finish = True
        self.update_peak_value()
        # logger.debug(f"笔 {self.idx} - {self.direction.name}, {self.start_value}=>{self.end_value} 添加缠K {chan_k.idx} 当前K列表：{self.k_idx}")

    def can_finish(self) -> bool:
        """
        判断笔是否可以算走完
        :return:
        """
        # 1、顶分型与底分型经过包含处理后，不允许共用 K 线，也就是不能有一 K 线分别属于顶分型与底分型，
        #    这条件和原来是一样的，这一点绝对不能放松，因为这样，才能保证足够的能量力度；
        if len(self.chan_k_list) < 6:  # 必须有趋势K
            return False
        # 2、在满足 1 的前提下，顶分型中最高 K 线和底分型的最低 K 线之间（不包括这两 K 线）
        #    ，不考虑包含关系，至少有 3 根（包括 3 根）以上 K 线。
        start_left, start, start_right = self.__start_fx()
        end_left, end, end_right = self.__end_fx()
        if len(self.chan_k_list) == 6 and len(start_right.klines) + len(end_left.klines) < 3:
            return False

        if start.is_included(end) or end.is_included(start):  # 分型顶点k线包含关系
            return False

        # 额外加的条件更符合直觉， 保证力度， 极点成笔
        high = max([x.high for x in self.chan_k_list])
        low = min([x.low for x in self.chan_k_list])
        if self.is_up:
            return high == end.high and max(start_left.high, start.high, start_right.high) < max(end_left.high, end.high, end_right.high)
        return low == end.low and max(start_left.high, start.high, start_right.high) > max(end_left.high, end.high, end_right.high)

    def __end_fx(self):
        return self.chan_k_list[-3], self.chan_k_list[-2], self.chan_k_list[-1]

    def __start_fx(self):
        return self.chan_k_list[0], self.chan_k_list[1], self.chan_k_list[2]

    def can_extend(self, value) -> bool:
        # logger.debug(f"笔 {self.idx} - {self.direction.name}, {self.start_value}=>{self.end_value} 新值：{value}")
        if self.is_up:
            return value < self.start_value

        return value > self.start_value

    def __str__(self):
        return f"BI({self.idx}[{self.start_value}, {self.end_value}])"


class ChanBIManager:
    """
    Bi 管理
    """

    def __init__(self, exclude_equal: bool = False):
        self.__chan_k_manager = ChanKManager(exclude_equal)
        self.__fx_manager = ChanFXManager()

        self.__chan_bi_list: List[ChanBI] = []  # 笔列表

    @overload
    def __getitem__(self, index: int) -> ChanBI:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[ChanBI]:
        ...

    def __getitem__(self, index: slice | int) -> List[ChanBI] | ChanBI:
        return self.__chan_bi_list[index]

    def __len__(self):
        return len(self.__chan_bi_list)

    def __iter__(self):
        return iter(self.__chan_bi_list)

    def is_empty(self):
        return len(self) == 0

    def update(self, k: G) -> ChanBI | None:
        """
        处理K线数据
        :param k: K线数据
        """
        chan_k = self.__chan_k_manager.update(k)  # 处理ChanK
        self.add_k(chan_k)
        fx = self.__fx_manager.fx
        if fx is None:
            return

        if len(self) == 0:  # 笔尚未开始
            self.create_bi(fx)

        elif self[-1].direction.is_up:  # 向上笔
            if fx.is_top and self[-1].can_finish():  # 出现顶分型
                self.create_bi(fx)
            if fx.is_bottom and self[-1].can_extend(self.__fx_manager.peak_value):  # 底分型
                self.try_extend_bi()
        elif self[-1].direction.is_down:  # 向下笔
            if fx.is_bottom and self[-1].can_finish():  # 底分型
                self.create_bi(fx)
            if fx.is_top and self[-1].can_extend(self.__fx_manager.peak_value):  # 出现顶分型
                self.try_extend_bi()
        if not self.is_empty():
            return self[-1]

    def try_extend_bi(self):
        """
        尝试做笔延伸
        """
        if len(self) == 1:  # 只有一笔 无法延伸
            self.__chan_bi_list = []
            self.create_bi(self.__fx_manager.fx)
            return

        # logger.info(f"笔 {self[-2].idx}:  {self[-2].k_idx} 延伸 {self[-1].k_idx}")
        self[-2].merge(self[-1])
        del self.__chan_bi_list[-1]
        self.create_bi(self.__fx_manager.fx)

    def create_bi(self, fx):
        """
        创建笔
        """
        bi = ChanBI(self.__fx_manager.lst, False, ChanDirection.DOWN if fx.is_top else ChanDirection.UP)
        # logger.debug(f"当前笔列表：{[bi.idx for bi in self.__chan_bi_list]}")
        bi.idx = 0
        if len(self) > 0:
            self[-1].next = bi
            bi.pre = self[-1]
            bi.idx = self[-1].idx + 1

        if len(self) > 1:
            self[-2].is_finish = True
        # logger.debug(f"创建新笔 {bi.idx}, k列表：{bi.k_idx}")
        self.__chan_bi_list.append(bi)

    def add_k(self, chan_k: ChanK):
        """
        添加K线到列表
        :param chan_k: 待添加K线
        :return:
        """
        self.__fx_manager.next(chan_k)
        if len(self) > 0:
            self[-1].add_chan_k(chan_k)


if __name__ == '__main__':
    pass
