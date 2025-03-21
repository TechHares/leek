#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/21 22:14
# @Author  : shenglin.li
# @File    : zs.py
# @Software: PyCharm
from copy import copy
from itertools import count
from typing import List, Dict

from leek.common import logger
from leek.t.chan.comm import ChanUnion


class ChanZS(ChanUnion):
    """
    中枢  可递归表达
    """

    def __init__(self, into_ele: ChanUnion, init_level: int = 1):
        assert into_ele.is_finish
        super().__init__(direction=into_ele.direction, high=None, low=None)

        self.init_level = init_level  # 初始中枢级别
        self.level = init_level  # 中枢级别  记录中枢升级情况
        self.up_line = None  # 中枢上轨
        self.down_line = None  # 中枢下轨

        self.is_merge = False  # 中枢是否被合并
        self.is_satisfy = False  # 中枢是否成立
        self.into_ele: ChanUnion = into_ele  # 进入段
        self.out_ele: ChanUnion | None = None  # 离开段
        self.element_list: List[ChanUnion] = []  # 次级别元素 笔 线段 中枢 走势 等

    def mark_on_data(self):
        ...

    def _merge(self, other: 'ChanUnion'):
        # 不支持合并
        raise NotImplementedError()

    @property
    def start_origin_k(self):
        return self.into_ele.start_origin_k

    @property
    def end_origin_k(self):
        return self.out_ele.end_origin_k if self.out_ele else self.element_list[-1].end_origin_k

    @property
    def start_value(self):
        return self.into_ele.start_value

    @property
    def end_value(self):
        return self.out_ele.end_value if self.out_ele else self.element_list[-1].end_value

    def __copy__(self):
        zs = ChanZS(self.into_ele, init_level=self.init_level)
        zs.level = self.level
        zs.up_line = self.up_line
        zs.down_line = self.down_line
        zs.is_satisfy = self.is_satisfy
        zs.into_ele = self.into_ele
        zs.out_ele = self.out_ele
        zs.element_list = self.element_list[:]

        zs.direction = self.direction
        zs.high = self.high
        zs.low = self.low
        zs.is_finish = self.is_finish
        return zs

    def expand(self, zs: 'ChanZS'):
        assert zs.direction == self.direction
        self.level += 1
        self.up_line = max(self.up_line, zs.up_line)
        self.down_line = min(self.down_line, zs.down_line)
        self.out_ele = zs.out_ele
        self.element_list = [self.into_ele.next]
        while self.element_list[-1].idx + 1 < self.out_ele.idx:
            self.element_list.append(self.element_list[-1].next)
        self.high = max([ele.high for ele in self.element_list])
        self.low = min([ele.low for ele in self.element_list])

    @property
    def start_timestamp(self):
        return self.element_list[0].start_timestamp

    @property
    def size(self):
        if self.is_finish:
            return len(self.element_list)
        if self.is_satisfy:
            return len([e for e in self.element_list if max(self.down_line, e.low) < min(e.high, self.up_line)])
        return 0

    @property
    def end_timestamp(self):
        return self.element_list[-1].end_timestamp

    def try_add_element(self, ele: ChanUnion, allow_similar_zs=False) -> bool | None:
        """
        尝试添加元素
        :param allow_similar_zs: 是否允许类中枢
        :param ele: 元素
        :return: True(zs完成) or False(zs破坏) or None(继续)
        """
        # 添加元素
        if len(self.element_list) == 0 or self.element_list[-1].idx < ele.idx:
            self.element_list.append(ele)
        elif self.element_list[-1].idx == ele.idx:
            self.element_list[-1] = ele
        else:
            raise RuntimeError("元素断层")

        self.update_state(allow_similar_zs)
        all_finish = len(self.element_list) >= 3 and all(ele.is_finish for ele in self.element_list[:3])
        if all_finish and not self.is_satisfy:  # 确认不成立
            self.is_finish = all_finish
            return False

        if self.is_satisfy:
            self.is_satisfy = all_finish
            if self.level == 0:
                return self.calc_similar_zs()
            else:
                rs = self.calc_zs()
                if rs is not None and not rs and allow_similar_zs:
                    return self.calc_similar_zs()
                return rs

    def update_state(self, allow_similar_zs=False):
        """
        更新状态
        @param allow_similar_zs: 是否允许类中枢
        """
        if len(self.element_list) < 3 or self.is_satisfy:
            return

        # 重置状态数据
        self.down_line = None
        self.up_line = None
        self.high = None
        self.low = None
        if self.is_up:
            down_line = max(self.element_list[1].low, self.element_list[2].low)
            up_line = min(self.element_list[0].high, self.element_list[1].high)
        else:
            down_line = max(self.element_list[0].low, self.element_list[1].low)
            up_line = min(self.element_list[1].high, self.element_list[2].high)
        if not self._is_valid():
            return

        if up_line > down_line: # 中枢成立
            self.high = max([ele.high for ele in self.element_list])
            self.low = min([ele.low for ele in self.element_list])
            self.up_line = up_line
            self.down_line = down_line
            self.is_satisfy = True
            self.level = 1
            return

        # 中枢不成立 构造类中枢
        if not allow_similar_zs:
            return

        self.level = 0 # 无级别中枢  类中枢
        self.is_satisfy = True

    def calc_similar_zs(self):
        if not all(ele.is_finish for ele in self.element_list[:3]):
            return None

        self.is_satisfy = False
        self.is_finish = True
        if not self._is_valid():
            return False
        if self.is_up:
            if self.element_list[1].end_value < self.into_ele.end_value:
                return False
        else:
            if self.element_list[1].end_value > self.into_ele.end_value:
                return False

        self.level = 0
        self.out_ele = self.element_list[1]
        self.element_list = self.element_list[:1]
        self.down_line = self.element_list[0].low
        self.up_line = self.element_list[0].high
        self.high = self.up_line
        self.low = self.down_line
        self.is_finish = True
        self.is_satisfy = True
        return True

    def _is_valid(self):
        if self.is_up:
            return self.element_list[0].end_value > self.into_ele.start_value
        else:
            return self.element_list[0].end_value < self.into_ele.start_value

    def calc_zs(self):
        try:
            for idx in range(3, len(self.element_list)):
                ele = self.element_list[idx]
                if max(self.down_line, ele.low) < min(ele.high, self.up_line):  # 在中枢之内
                    continue  # 继续延伸

                if not ele.is_finish:
                    return None
                peak_value = max(e.high for e in self.element_list[:3]) if self.is_up else min(e.low for e in self.element_list[:3])
                for i in range(3, idx):
                    if self.direction != self.element_list[i].direction:
                        continue
                    if self.is_up and self.element_list[i].high > peak_value:
                        peak_value = self.element_list[i].high
                        self.out_ele = self.element_list[i]
                    if self.direction.is_down and self.element_list[i].low < peak_value:
                        peak_value = self.element_list[i].low
                        self.out_ele = self.element_list[i]
                if self.out_ele is not None:
                    self.element_list = self.element_list[:self.element_list.index(self.out_ele)]
                    self.is_finish = True
                    return True
                return False
        finally:
            if self.is_finish:
                self.high = max([ele.high for ele in self.element_list])
                self.low = min([ele.low for ele in self.element_list])

    # def calc_zs(self):
    #     try:
    #         for idx in range(3, len(self.element_list)):
    #             ele = self.element_list[idx]
    #             if max(self.down_line, ele.low) < min(ele.high, self.up_line):  # 在中枢之内
    #                 continue  # 继续延伸
    #
    #             if not ele.is_finish:
    #                 return None
    #
    #             if ele.direction == self.direction:  # 走势完成 & 笔方向与中枢方向相同
    #                 tmp_out_ele_idx = 0
    #                 for i in range(len(self.element_list)-1, -1, -1):
    #                     if self.element_list[i].direction != self.direction:
    #                         continue
    #                     if self.is_up  and self.element_list[i].high >= self.high:
    #                         tmp_out_ele_idx = i
    #                         break
    #                     if not self.is_up and self.element_list[i].low <= self.low:
    #                         tmp_out_ele_idx = i
    #                         break
    #
    #                 if tmp_out_ele_idx >= 3:
    #                     self.out_ele = self.element_list[tmp_out_ele_idx]
    #                     self.element_list = self.element_list[:tmp_out_ele_idx]
    #                     self.is_finish = True
    #                     return True
    #                 return False
    #             if ele.direction != self.direction:  # 走势完成 & 笔方向与中枢方向不同
    #                 self.out_ele = self.element_list[idx-1]
    #                 self.element_list = self.element_list[:idx-1]
    #                 self.is_finish = True
    #                 return True
    #     finally:
    #         if self.is_finish:
    #             self.high = max([ele.high for ele in self.element_list])
    #             self.low = min([ele.low for ele in self.element_list])

    def __str__(self):
        return (f"ZS[{self.idx}]({self.down_line}-{self.up_line}, lv={self.level}, into={self.into_ele}, "
                f"els={[str(e) for e in self.element_list]}, out={self.out_ele})")

class ChanZSManager:
    def __init__(self, max_level=3, allow_similar_zs=False, enable_expand=True, enable_stretch=True):
        self.max_level = max_level
        self.enable_expand = enable_expand
        self.enable_stretch = enable_stretch
        self.allow_similar_zs = allow_similar_zs

        self.zs_list: List[ChanZS] = []
        self._idx = 0
        self.cur_zs: ChanZS | None = None

        self.tmp_list: List[ChanUnion] = []  # 临时ele列表

    def update(self, chan: ChanUnion):
        assert len(self.tmp_list) == 0 or self.tmp_list[-1].idx <= chan.idx
        if len(self.tmp_list) == 0 or self.tmp_list[-1].idx+1 == chan.idx:
            self.tmp_list.append(chan)
        elif self.tmp_list[-1].idx == chan.idx:
            self.tmp_list[-1] = chan
        else:
            self.update(chan.pre)
            self.update(chan)
            return

        if self.cur_zs is None:
            self.zs_create()
            return
        res = self.cur_zs.try_add_element(chan, self.allow_similar_zs)
        self.sz_stretch()
        if res is None:
            return

        if res:  # 中枢完成 开启下一段
            self.add_zs(self.cur_zs)
            self.zs_expand()
            self.tmp_list = self.tmp_list[self.tmp_list.index(self.cur_zs.out_ele):]
        # 中枢破坏
        self.cur_zs = None
        self.update(chan)

    def zs_create(self):
        """
        创建中枢
        :return:
        """
        if len(self.tmp_list) == 0 or not self.tmp_list[0].is_finish:
            return
        self.cur_zs = ChanZS(self.tmp_list[0])
        self._idx += 1
        self.cur_zs.idx = self._idx
        if len(self.zs_list) > 0:
            self.zs_list[-1].link_next(self.cur_zs, False)

        tmp = self.tmp_list[1:]
        self.tmp_list = []
        for e in tmp:
            self.update(e)

    def add_zs(self, zs: ChanZS):
        """
        添加中枢
        :param zs:
        :return:
        """
        lst = self.zs_list
        if len(lst) > 0:
            lst[-1].link_next(zs, False)
        lst.append(zs)

    def zs_extend(self):
        """
        中枢扩张, 指出现第3类买卖点后，随后的股价离开没有继续创新高，马上又回到中枢区间范围内（需要注意是回到中枢区间以内）。

        PS: 实际效果看到，这是中枢延伸的一种形式， 该情况下延伸之中也能完成升级， 如想找出这样的中枢， 不如升级次级别走势(如笔升段， 段升 段'，K线采用更长期等方式)来的直接
        :return:
        """
        ...

    def zs_expand(self):
        """
        中枢扩展，就是指两个同级别同方向的中枢之间出现相互接触，哪怕一个瞬间的波动也算。简单来说，中枢扩展是：同级别、同方向、有接触的。
        :param
        :return:
        """
        if not self.enable_expand:
            return
        expand_res = []
        zs_list = self.zs_list
        if len(zs_list) < 2:
            return

        pre = zs_list[-2]
        cur = zs_list[-1]
        if pre.level == 0 or cur.level == 0:
            return
        if pre.direction != cur.direction or pre.level > self.max_level or cur.level > self.max_level:
            return

        if (cur.is_up and cur.low < pre.high) or (not cur.is_up and cur.high > pre.low): # 存在接触
            zs = copy(pre)
            zs.expand(cur)
            expand_res.append(zs)
            pre.is_merge = True
            cur.is_merge = True
        for zs in expand_res:
            self.add_zs(zs)

    def sz_stretch(self):
        """
        中枢延伸指中枢没有结束之前，可以继续上下波动，这种情况下，所有围绕走势中枢产生的前后两个次级波动都必须至少有一个触及走势中枢的区间。另外要注意，一旦中枢延伸出现9段，中枢就会升级。
        :return:
        """
        if self.cur_zs is None or not self.enable_stretch or self.cur_zs.level == 0:
            return

        zs = self.cur_zs
        lv = zs.size // 9
        if lv > (zs.level - zs.init_level) and zs.level < self.max_level:  # 9段 触发升级
            zs.level += 1

        # 降级中枢 次级别延续可能导致 中枢升级错误
        if lv // 9 < zs.level - 1 and zs.level > 1:
            zs.level -= 1


if __name__ == '__main__':
    pass
