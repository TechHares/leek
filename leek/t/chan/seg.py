#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/18 20:34
# @Author  : shenglin.li
# @File    : seg.py
# @Software: PyCharm
from typing import List, overload

from leek.common import G, logger
from leek.t.chan.bi import ChanBI, ChanBIManager
from leek.t.chan.comm import ChanUnion, Merger, mark_data
from leek.t.chan.enums import ChanFX
from leek.t.chan.fx import ChanFXManager
from leek.t.chan.k import ChanK
from update import update


class ChanFeature(ChanUnion):
    """
    线段特征序列
    """

    def __init__(self, bi: ChanBI):
        super().__init__(direction=bi.direction, high=bi.high, low=bi.low, is_finish=bi.is_finish)
        self.idx = bi.idx
        self.bi_list = [bi]

    @property
    def size(self):
        return len(self.bi_list)
    @property
    def start_timestamp(self):
        return self.bi_list[0].start_timestamp

    @property
    def end_timestamp(self):
        return self.bi_list[-1].end_timestamp

    def mark_on_data(self):
        ...

    def _merge(self, other: 'ChanUnion'):
        assert isinstance(other, ChanFeature)
        self.bi_list.extend(other.bi_list)

    def __str__(self):
        return f"Feature({self.idx}[{self.start_value}, {self.end_value}])"


class ChanSegment(ChanUnion):
    """
    线段
    """

    def __init__(self, bi_list: List[ChanBI]):
        assert len(bi_list) > 0
        first_bi = bi_list[0]
        super().__init__(direction=first_bi.direction, high=first_bi.high, low=first_bi.low)

        self.bi_list = [first_bi]
        self.peak_point = first_bi
        self.be_break = False
        for bi in bi_list[1:]:
            self.add_bi(bi)

    def mark_on_data(self):
        mark_field = "seg" if self.is_finish else "seg_"
        self.bi_list[0].mark_on_data(mark_field, True, False)
        self.bi_list[-1].mark_on_data(mark_field, False, True)
        if not self.is_finish:
            self.peak_point.mark_on_data("seg_", False, True)

    def _merge(self, other: 'ChanUnion'):
        assert isinstance(other, ChanSegment)
        for idx in range(len(other.bi_list)):
            if self.bi_list[-1].idx < other.bi_list[idx].idx:
                self.bi_list.extend(other.bi_list[idx:])
                break

    @property
    def size(self):
        return len(self.bi_list)

    @property
    def start_timestamp(self):
        return self.bi_list[0].start_timestamp

    @property
    def end_timestamp(self):
        return self.bi_list[-1].end_timestamp

    def is_satisfy(self):
        return len(self.bi_list) >= 3

    def is_break(self):
        """
        判断线段是否被破坏
        :return:
        """
        bi = self.bi_list[-1]
        if bi.direction == self.direction:
            return False
        if self.be_break:
            return True
        pre = self.bi_list[-2]

        self.be_break = bi.low < pre.low if self.is_up else bi.high > pre.high
        # logger.debug(f"线段: {self.idx} 笔列表: {[bi.idx for bi in self.bi_list]} {self.peak_point.idx}, 是否被{bi.idx}"
        #              f"[{bi.start_value}, {bi.end_value}]破坏: "
        #              f"{self.be_break}")
        return self.be_break

    def add_bi(self, bi: ChanBI):
        """
        添加BI
        :param bi:
        :return:
        """
        if self.bi_list[-1].idx < bi.idx:
            self.bi_list.append(bi)
        if self.bi_list[-1].idx == bi.idx:
            self.bi_list[-1] = bi

        if self.direction != bi.direction:
            # 兼容发生笔延伸
            if len(self.bi_list) > 2:
                self.update_peak_point(self.bi_list[-2])
            return
        self.update_peak_point(bi)

    def update_peak_point(self, bi: ChanBI):
        if (self.is_up and bi.high > self.peak_point.high) or (not self.is_up and bi.low < self.peak_point.low):
            self.peak_point = bi

    def finish(self):
        """
        线段结束
        :return:
        """
        tmp = self.bi_list
        self.bi_list = [bi for bi in tmp if bi.idx <= self.peak_point.idx]
        if any(not bi.is_finish for bi in self.bi_list):  # 有笔未完成
            self.is_finish = False
            self.bi_list = tmp
            return []
        self.is_finish = True
        return [bi for bi in tmp if bi.idx > self.peak_point.idx]


class ChanSegmentManager:
    """
    线段 管理
    """

    def __init__(self):
        self.__seg_list: List[ChanSegment] = []

    @overload
    def __getitem__(self, index: int) -> ChanSegment:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[ChanSegment]:
        ...

    def __getitem__(self, index: slice | int) -> List[ChanSegment] | ChanSegment:
        return self.__seg_list[index]

    def __len__(self):
        return len(self.__seg_list)

    def __iter__(self):
        return iter(self.__seg_list)

    def create_seg(self, bi: ChanBI | List[ChanBI]):
        """
        创建线段
        :param bi:
        :return:
        """
        self.__seg_list.append(ChanSegment([bi] if isinstance(bi, ChanBI) else bi))
        if len(self) >= 2:
            self[-1].next = self[-2]
            self[-2].next = self[-1]
            self[-1].idx = self[-2].idx + 1

    def update(self, bi: ChanBI):
        """
        计算线段
        :param bi: 笔
        :return:
        """
        if len(self) == 0 or self[-1].is_finish:
            self.create_seg(bi)
        else:
            self[-1].add_bi(bi)
        self.try_confirm_first_seg()
        if self[-1].is_break():  # 线段被破坏
            self.calculate_seg()

    def try_confirm_first_seg(self):
        if len(self) != 1:  # 再次确认只有一段
            return

        seg_direction = self[-1].direction  # 线段方向
        bi_list = self[-1].bi_list
        if len(bi_list) < 3 or any([not b.is_finish for b in bi_list[:3]]):
            return
        # 第一段反复破的线段 无法确认 舍弃
        if seg_direction.is_up:
            if bi_list[2].high < bi_list[1].high:
                self.reset_start()
        else:
            if bi_list[2].low > bi_list[1].low:
                self.reset_start()


    def reset_start(self):
        bi_list = self[-1].bi_list
        self.__seg_list = []
        for bi in bi_list[1:]:
            self.update(bi)

    def calculate_seg(self):
        """
        计算线段
        :return:
        """
        bi_list = self[-1].bi_list
        if not self[-1].is_satisfy():
            assert self[-1].pre is None
            self.reset_start()
            return

        seg_direction = self[-1].direction  # 线段方向
        end_fx = ChanFX.TOP if seg_direction.is_up else ChanFX.BOTTOM  # 结束该线段的分型条件
        features = [ChanFeature(bi) for bi in bi_list if bi.direction != seg_direction]  # 反向笔形成特征
        point_idx = self[-1].peak_point.idx
        fx = self.find_fx(features, end_fx, point_idx + 1)
        if fx is None:
            return

        logger.debug(f"{self[-1].idx}找到分型，特征列表: {[str(f) for f in features]}, 找到: {end_fx}")
        if fx.gap:  # 有缺口
            if self.find_fx([ChanFeature(bi) for bi in bi_list if bi.direction == seg_direction and bi.idx >= point_idx],
                            end_fx.reverse, 0) is None:
                return
        next_bi_list = self[-1].finish()
        for bi in next_bi_list:
            self.update(bi)

    def find_fx(self, feature_list: List[ChanFeature], fx: ChanFX, point_idx):
        if len(feature_list) < 3:
            return None
        # logger.debug(f"{self[-1].idx}特征列表: {[str(f) for f in feature_list]}, {point_idx}, 寻找分型: {fx.name}")
        fx_manager = ChanFXManager()
        pre = feature_list[0]
        fx_manager.next(pre)
        for cur in feature_list[1:]:

            # 特征合并
            merger = Merger(just_included=cur.idx <= point_idx)
            pre.link_next(cur)
            if merger.can_merge(pre, cur):
                pre.merge(cur)
                cur = pre

            # 判断分型
            # if fx_manager.next(cur) == fx and (fx_manager.point.idx == point_idx or point_idx == 0):
            if fx_manager.next(cur) == fx:
                return fx_manager


if __name__ == '__main__':
    pass
