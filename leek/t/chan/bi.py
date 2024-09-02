#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/16 21:33
# @Author  : shenglin.li
# @File    : bi.py
# @Software: PyCharm
from typing import List, overload

from leek.common import G, logger
from leek.t.chan.comm import ChanUnion, mark_data
from leek.t.chan.enums import ChanFX, ChanDirection, BiFXValidMethod
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

    def mark_on_data(self, mark_field=None, mark_start=True, mark_end=True):
        if mark_field is None:
            mark_field = "bi" if self.is_finish else "bi_"

        def find_origin_k(ck: ChanK, value):
            for k in ck.klines:
                if ck.is_up and k.high == value:
                    return k
                if not ck.is_up and k.low == value:
                    return k
            return ck.klines[-1]

        if mark_start:
            mark_data(find_origin_k(self.chan_k_list[1], self.start_value), mark_field, self.start_value)
        if mark_end:
            mark_data(find_origin_k(self.chan_k_list[-2], self.end_value), mark_field, self.end_value)

    def add_chan_k(self, chan_k: ChanK):
        if self.chan_k_list[-1].idx < chan_k.idx:
            self.chan_k_list.append(chan_k)
        else:
            self.chan_k_list[-1] = chan_k
        if self.pre is not None and len(self.chan_k_list) > 5:  # 尝试提前结束前笔
            if ((self.is_up and max([x.high for x in self.chan_k_list[:3]]) < min([x.low for x in self.chan_k_list[-2:]]))
                    or (not self.is_up and min([x.low for x in self.chan_k_list[:3]]) < max([x.high for x in self.chan_k_list[-2:]]))):
                self.pre.is_finish = True
        self.update_peak_value()
        # logger.debug(f"笔 {self.idx} - {self.direction.name}, {self.start_value}=>{self.end_value} 添加缠K {chan_k.idx} 当前K列表：{self.k_idx}")

    def can_finish(self, valid_method: BiFXValidMethod = BiFXValidMethod.NORMAL) -> bool:
        """
        判断笔是否可以算走完
        :param valid_method: 校验方法
        :return:
        """
        if self.chan_k_list[1].is_included(self.chan_k_list[-2]):  # k线包含关系
            return False

        if len(self.chan_k_list) < 6 or (len(self.chan_k_list) == 6 and valid_method != BiFXValidMethod.LOSS):  # 除宽松之外必须有趋势K
            return False

        if self.is_up:
            return self.__can_finish_up(valid_method)
        return self.__can_finish_down(valid_method)

    def __can_finish_down(self, valid_method):
        assert not self.is_up
        start_left, start, start_right = self.__start_fx()  # 顶
        end_left, end, end_right = self.__end_fx()  # 底

        if valid_method == BiFXValidMethod.NORMAL:  # 顶分型的最高点比底分型中间元素高点还高
            return start.high > end.high

        if valid_method == BiFXValidMethod.HALF:  # 前两元素高低点限制
            return start.high > min(end_left.high, end.high) and max(start_right.low, start.low) > end.low

        if valid_method == BiFXValidMethod.STRICT:  # 三元素高低点限制
            return start.high > min(end_left.high, end.high, end_right.high) \
                   and max(start_left.low, start.low, start_right.low) > end.low

        if valid_method == BiFXValidMethod.TOTALLY:  # 顶分型3元素的最低点必须比底分型三元素的最高点还高
            return max(start_left.low, start.low, start_right.low) > min(end_left.high, end.high, end_right.high)

        #  LOSS 分型成立且不违背方向
        return end.low < start.high

    def __can_finish_up(self, valid_method):
        assert self.is_up
        start_left, start, start_right = self.__start_fx()  # 底
        end_left, end, end_right = self.__end_fx()  # 顶
        if valid_method == BiFXValidMethod.NORMAL:  # 底分型的最低点比顶分型中间元素低点还低
            return start.low < end.low

        if valid_method == BiFXValidMethod.HALF:  # 前两元素高低点限制
            return start.low < min(end_left.low, end.low) and max(start_right.high, start.high) < end.high

        if valid_method == BiFXValidMethod.STRICT:  # 三元素高低点限制
            return start.low < min(end_left.low, end.low, end_right.low) \
                   and max(start_left.high, start.high, start_right.high) < end.high

        if valid_method == BiFXValidMethod.TOTALLY:  # 底分型3元素的最高点必须必顶分型三元素的最低点还低
            return max(start_left.high, start.high, start_right.high) < min(end_left.low, end.low, end_right.low)

        #  LOSS 分型成立且不违背方向
        return end.high > start.low

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

    def __init__(self, just_included: bool = False, exclude_equal: bool = False,
                 bi_valid_method: BiFXValidMethod = BiFXValidMethod.NORMAL):
        self.__chan_k_manager = ChanKManager(just_included, exclude_equal)
        self.__fx_manager = ChanFXManager()

        self.bi_valid_method = bi_valid_method
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

    def update(self, k: G):
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
            if fx.is_top and self[-1].can_finish(self.bi_valid_method):  # 出现顶分型
                self.create_bi(fx)
            if fx.is_bottom and self[-1].can_extend(self.__fx_manager.peak_value):  # 底分型
                self.try_extend_bi()
        elif self[-1].direction.is_down:  # 向下笔
            if fx.is_bottom and self[-1].can_finish(self.bi_valid_method):  # 底分型
                self.create_bi(fx)
            if fx.is_top and self[-1].can_extend(self.__fx_manager.peak_value):  # 出现顶分型
                self.try_extend_bi()

    def try_extend_bi(self):
        """
        尝试做笔延伸
        """
        if len(self) == 1:  # 只有一笔 无法延伸
            self.__chan_bi_list = []
            self.create_bi(self.__fx_manager.fx)
            return

        # logger.debug(f"笔 {self[-2].idx}:  {self[-2].k_idx} 延伸 {self[-1].k_idx}")
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
