#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/18 20:34
# @Author  : shenglin.li
# @File    : seg.py
# @Software: PyCharm
from typing import List, overload

from rich.segment import Segment

from leek.common import logger, G
from leek.t.chan.bi import ChanBI, ChanBIManager
from leek.t.chan.comm import ChanUnion, Merger, mark_data
from leek.t.chan.enums import ChanFX, BiFXValidMethod, ChanDirection
from leek.t.chan.fx import ChanFXManager


class ChanFeature(ChanUnion):
    """
    线段特征序列
    """

    def __init__(self, bi: ChanBI):
        super().__init__(direction=bi.direction.reverse(), high=bi.high, low=bi.low, is_finish=bi.is_finish)
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

        self.peak_point = None
        self.left_feature = None
        self.middle_feature = None
        self.right_feature = None
        self.gap = None

        for bi in bi_list[1:]:
            self.add_bi(bi)

    def mark_on_data(self):
        mark_field = "seg" if self.is_finish else "seg_"
        mark_data(self.bi_list[0].start_origin_k, mark_field, self.bi_list[0].start_value)
        mark_data(self.bi_list[-1].end_origin_k, mark_field, self.bi_list[-1].end_value)
        if not self.is_finish and self.peak_point:
            mark_data(self.peak_point.end_origin_k, mark_field, self.bi_list[-1].end_value)
        mk = self.get_middle_k()
        mark_data(mk, "seg_value", (self.start_value + self.end_value) / 2)
        mark_data(mk, "seg_idx", self.idx)

    @property
    def start_origin_k(self):
        return self.bi_list[0].start_origin_k

    @property
    def end_origin_k(self):
        return self.bi_list[-1].end_origin_k

    def get_middle_k(self):
        """
        获取线段中间K
        :return:
        """
        ts = (self.end_timestamp + self.start_timestamp) // 2
        for bi in self.bi_list:
            k = bi.get_k_by_ts(ts)
            if k is not None:
                return k
        return None

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

    @property
    def start_value(self):
        return self.bi_list[0].start_value

    @property
    def end_value(self):
        return self.bi_list[-1].end_value

    def is_satisfy(self):
        # 前三笔必须有重叠
        return len(self.bi_list) >= 3 and (self.is_up and self.bi_list[2].high > self.bi_list[0].low
                                           or not self.is_up and self.bi_list[2].low < self.bi_list[0].high)

    def is_break(self):
        """
        判断线段是否被破坏
        :return:
        """
        if self.left_feature is None or self.middle_feature is None or self.right_feature is None:
            return False

        self.gap = (self.is_up and self.left_feature.high < self.middle_feature.low
               or not self.is_up and self.left_feature.low > self.middle_feature.high)

        if not self.gap:
            # middle 既是高点也是低点的情况处理
            if (self.is_up and self.middle_feature.low < self.right_feature.low) or (not self.is_up and self.middle_feature.high > self.right_feature.high):
                for tmp_bi in self.bi_list:
                    if tmp_bi.idx <= self.right_feature.bi_list[-1].idx:
                        continue
                    if (self.is_up and tmp_bi.low < self.middle_feature.low) or (not self.is_up and tmp_bi.high > self.middle_feature.high):
                        return True
                return False
            return True
        return self.gap_break()

    def gap_break(self):
        """
        存在缺口的情况下是否被破坏
        :return:
        """
        fb = [bi for bi in self.bi_list if bi.idx > self.peak_point.idx]
        if len(fb) == 0:
            return False
        self.next = ChanSegment(fb)
        self.next.pre = self
        return self.next.is_satisfy() and self.next.right_feature is not None

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

        self.update_peak_value()
        if len(bi.chan_k_list) < 6: # 确保笔不会被前一笔延伸
            return

        self.update_feature()

    def update_peak_value(self):
        """
        更新极值 信息
        """
        self.high = max([x.high for x in self.bi_list])
        self.low = min([x.low for x in self.bi_list])

        if len(self.bi_list) < 3:
            return
        pre_peak_point = self.peak_point
        if self.peak_point is None:
            # 第三笔新高或新低 极值保底成立
            fb = [bi for bi in self.bi_list if bi.direction == self.direction]
            for i in range(1, len(fb)):
                if (fb[i].high > fb[i - 1].high and self.is_up) or (not self.is_up and fb[i].low < fb[i - 1].low):
                    self.peak_point = fb[i]
                    break
        if self.peak_point is None:
            return

        assert self.peak_point is not None and self.peak_point.direction == self.direction, "极值点方向错误"
        if self.is_up: # 向上线段
            if self.bi_list[-1].direction.is_up: # 最后一笔是向上笔
                self.peak_point = max(self.peak_point, self.bi_list[-1], key=lambda x: x.high)
            else: # 最后一笔是向上笔
                self.peak_point = max(self.peak_point, self.bi_list[-2], key=lambda x: x.high)
        else: # 向下线段
            if self.bi_list[-1].direction.is_up: # 最后一笔是向上笔
                self.peak_point = min(self.peak_point, self.bi_list[-2], key=lambda x: x.low)
            else: # 最后一笔是向上笔
                self.peak_point = min(self.peak_point, self.bi_list[-1], key=lambda x: x.low)

        if pre_peak_point != self.peak_point:
            self.middle_feature = None
            self.right_feature = None
            self.update_left_feature()


    def update_left_feature(self):
        """
        更新左侧特征分型
        :return:
        """
        if len(self.bi_list) < 3:
            return

        fb = [bi for bi in self.bi_list if bi.direction != self.direction and bi.idx < self.peak_point.idx]
        if len(fb) == 0:
            return
        fb.reverse()
        self.left_feature = ChanFeature(fb[0])
        fb = fb[1:]
        for bi in fb:
            feature = ChanFeature(bi)
            if feature.is_included(self.left_feature, True):
                feature.merge(self.left_feature)
                self.left_feature = feature
            else:
                break

    def update_feature(self):
        """
        更新顶点和右侧特征分型
        :return:
        """
        if self.left_feature is None:
            return
        fb = [bi for bi in self.bi_list if bi.direction != self.direction and bi.idx > self.peak_point.idx]
        if len(fb) == 0 or self.right_feature is not None and self.right_feature.bi_list[-1].idx < fb[-1].idx: # 不影响分型的情况下取消计算
            return
        features = []
        for bi in fb:
            feature = ChanFeature(bi)
            feature.direction = self.direction
            if len(features) > 0 and features[-1].is_included(feature, True):
                features[-1].merge(feature)
            else:
                features.append(feature)
            if len(features) == 3:
                break
        if len(features) >= 2:
            self.middle_feature = features[0]
            self.right_feature = features[1]
        else:
            self.middle_feature = None
            self.right_feature = None

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
        # 重新更新高低点
        self.high = max([x.high for x in self.bi_list])
        self.low = min([x.low for x in self.bi_list])
        self.is_finish = True
        if self.gap:
            return self.next, self.next.finish()[1]
        return None, [bi for bi in tmp if bi.idx > self.peak_point.idx]


class ChanSegmentManager:
    """
    线段 管理
    """

    def __init__(self):
        self.__seg_list: List[ChanSegment] = []

        self.tmp_bi_list = [] # 用于未确认段起始点存放临时的笔

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

    def is_empty(self):
        return len(self) == 0

    def create_seg(self, bi: ChanSegment | ChanBI | List[ChanBI]):
        """
        创建线段
        :param bi:
        :return:
        """
        if isinstance(bi, ChanSegment):
            self.__seg_list.append(bi)
        else:
            self.__seg_list.append(ChanSegment([bi] if isinstance(bi, ChanBI) else bi))
        if len(self) > 1:
            self[-1].pre = self[-2]
            self[-2].next = self[-1]
            self[-1].idx = self[-2].idx + 1

    def update_bi(self, bi: ChanBI):
        """
        计算线段
        :param bi: 笔
        :return:
        """
        if len(self) == 0 :
            self.try_confirm_first_seg(bi)
        elif self[-1].is_finish:
            self.create_seg(bi)
        else:
            self[-1].add_bi(bi)
            if self[-1].is_break():  # 线段被破坏
                next_seg, next_bi_list = self[-1].finish()
                if next_seg:
                    self.create_seg(next_seg)
                for bi in next_bi_list:
                    self.update_bi(bi)
        if len(self) >= 1:
            return self[-1]

    def try_confirm_first_seg(self, bi: ChanBI):
        if len(self.tmp_bi_list) == 0 or self.tmp_bi_list[-1].idx < bi.idx:
            self.tmp_bi_list.append(bi)
        else:
            self.tmp_bi_list[-1] = bi

        if len(self.tmp_bi_list) < 10:
            return
        if self.tmp_bi_list[0].direction.is_up:
            high_bi = max(self.tmp_bi_list, key=lambda x: x.end_value)
            high_bi_idx = self.tmp_bi_list.index(high_bi) + 1
            low_bi = min(self.tmp_bi_list, key=lambda x: x.start_value)
            low_bi_idx = self.tmp_bi_list.index(low_bi)
        else:
            high_bi = max(self.tmp_bi_list, key=lambda x: x.start_value)
            high_bi_idx = self.tmp_bi_list.index(high_bi)
            low_bi = min(self.tmp_bi_list, key=lambda x: x.end_value)
            low_bi_idx = self.tmp_bi_list.index(low_bi) + 1

        idx = min(high_bi_idx, low_bi_idx) # 出现在同一笔内 向后取  否则取先比
        if abs(high_bi_idx - low_bi_idx) == 1:
            idx = max(high_bi_idx, low_bi_idx)
        if idx + 5 > len(self.tmp_bi_list): # 后面至少空余5笔
            return
        self.create_seg(self.tmp_bi_list[idx])
        for bi in self.tmp_bi_list[idx + 1:]:
            self.update_bi(bi)
        self.tmp_bi_list = None

    def reset_start(self):
        bi_list = self[-1].bi_list
        self.__seg_list = []
        for bi in bi_list[1:]:
            self.update_bi(bi)



if __name__ == '__main__':
    pass
