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
    中枢/走势  可递归表达
    """

    def __init__(self, into_ele: ChanUnion, init_level: int = 1):
        assert into_ele.is_finish
        super().__init__(direction=into_ele.direction, high=None, low=None)

        self.init_level = init_level  # 初始中枢级别
        self.level = init_level  # 中枢级别  记录中枢升级情况
        self.up_line = None  # 中枢上轨
        self.down_line = None  # 中枢下轨

        self.is_satisfy = False  # 中枢是否成立
        self.into_ele: ChanUnion = into_ele  # 进入段
        self.out_ele: ChanUnion | None = None  # 离开段
        self.element_list: List[ChanUnion] = []  # 次级别元素 笔 线段 中枢 走势 等

    def mark_on_data(self):
        ...

    def _merge(self, other: 'ChanUnion'):
        # 不支持合并
        raise NotImplementedError()

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
        assert zs.level == self.level
        assert zs.direction == self.direction
        self.level += 1
        self.up_line = max(self.up_line, zs.up_line)
        self.down_line = min(self.down_line, zs.down_line)
        self.out_ele = zs.out_ele
        self.element_list = [self.into_ele.next]
        while self.element_list[-1].idx + 1 < self.out_ele.idx:
            self.element_list.append(self.element_list[-1].next)
        self.update_peak_value(len(zs.element_list), True)

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

    def try_add_element(self, ele: ChanUnion, just_cal_list: bool = False) -> bool | None:
        """
        尝试添加元素
        :param ele: 元素
        :param just_cal_list: 是否只计算构成列表
        :return: True(zs完成) or False(zs破坏) or None(继续)
        """
        if len(self.element_list) == 0 or self.element_list[-1].idx < ele.idx:
            self.element_list.append(ele)
        if self.element_list[-1].idx == ele.idx:
            self.element_list[-1] = ele

        if self.is_satisfy:  # 中枢已经成立
            return self.calc_zs(just_cal_list)

        # 还未确认中枢存在
        if len(self.element_list) < 3:
            return None

        all_finish = all([e.is_finish for e in self.element_list[:3]])

        self.update_peak_value(2, just_cal_list)
        self.is_satisfy = self.update_line()
        # logger.debug(f"{self}, all_finish={all_finish}, satisfy={self.is_satisfy}")
        if all_finish and not self.is_satisfy:  # 不成立
            return False

        if self.is_satisfy:
            self.is_satisfy = all_finish
            return self.calc_zs(just_cal_list)

    def calc_zs(self, just_cal_list: bool = False):
        for idx in range(3, len(self.element_list)):
            ele = self.element_list[idx]
            if max(self.down_line, ele.low) < min(ele.high, self.up_line):  # 在中枢之内
                self.update_peak_value(idx, just_cal_list)
                continue  # 继续延伸

            if not ele.is_finish:
                return None

            if ele.direction == self.direction:  # 走势完成 & 笔方向与中枢方向相同
                tmp_out_ele_idx = 0
                for i in range(len(self.element_list)):
                    if self.element_list[i].direction != self.direction:
                        continue
                    if self.is_up  and self.element_list[i].high >= self.high:
                        tmp_out_ele_idx = i
                        break
                    if not self.is_up and self.element_list[i].low <= self.low:
                        tmp_out_ele_idx = i
                        break

                if tmp_out_ele_idx >= 3:
                    self.out_ele = self.element_list[tmp_out_ele_idx]
                    self.element_list = self.element_list[:tmp_out_ele_idx]
                    self.is_finish = True
                    return True
                return False
            if ele.direction != self.direction:  # 走势完成 & 笔方向与中枢方向不同
                self.out_ele = self.element_list[idx-1]
                self.element_list = self.element_list[:idx-1]
                self.is_finish = True
                return True

    def simulation_compute(self):
        """
        todo: 假设当前所有元素已完成 进行模拟计算
        :return:
        """
        if not self.is_satisfy:
            return
        zs = self.__copy__()
        zs_element_list = zs.element_list

    def update_line(self) -> bool:
        self.up_line = min([ele.high for ele in self.element_list[:3]])
        self.down_line = max([ele.low for ele in self.element_list[:3]])
        return self.down_line < self.up_line and ((self.is_up and self.into_ele.low <= self.low) or
                                                  (not self.is_up and self.into_ele.high >= self.high))

    def update_peak_value(self, idx, just_cal_list):
        """
        更新最高/低值
        :param idx: 元素坐标
        :param just_cal_list: 只计算中枢？
        :return:
        """
        h = []
        l = []
        if len(self.element_list) > 0:
            h.append(max([ele.high for ele in self.element_list[:idx+1]]))
            l.append(min([ele.low for ele in self.element_list[:idx+1]]))
        if not just_cal_list:
            if self.into_ele is not None:
                h.append(self.into_ele.high)
                l.append(self.into_ele.low)
            if self.out_ele is not None:
                h.append(self.out_ele.high)
                l.append(self.out_ele.low)
        if len(h) > 0:
            self.high = max(h)
            self.low = min(l)

    def __str__(self):
        return (f"ZS[{self.idx}]({self.down_line}-{self.up_line}, lv={self.level}, into={self.into_ele}, "
                f"els={[str(e) for e in self.element_list]}, out={self.out_ele})")


class ChanZSManager:
    def __init__(self, just_cal_list: bool = True, max_level=3, enable_expand=True, enable_stretch=True):
        self.just_cal_list = just_cal_list
        self.max_level = max_level
        self.enable_expand = enable_expand
        self.enable_stretch = enable_stretch

        self.zs_dict: Dict[int, List[ChanZS]] = {}
        self._idx = 0
        self.cur_zs: ChanZS | None = None

        self.tmp_list: List[ChanUnion] = []  # 临时ele列表

    def update(self, chan: ChanUnion):
        if len(self.tmp_list) == 0 or self.tmp_list[-1].idx < chan.idx:
            self.tmp_list.append(chan)
        if self.tmp_list[-1].idx == chan.idx:
            self.tmp_list[-1] = chan

        if self.cur_zs is None:
            self.zs_create()
            return
        res = self.cur_zs.try_add_element(chan, self.just_cal_list)
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
        if self.cur_zs.level in self.zs_dict and len(self.zs_dict[self.cur_zs.level]) > 0:
            self.zs_dict[self.cur_zs.level][-1].link_next(self.cur_zs, False)

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
        if zs.level not in self.zs_dict:
            self.zs_dict[zs.level] = []

        lst = self.zs_dict[zs.level]
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
        for level in self.zs_dict:
            if level >= self.max_level:
                continue
            zs_list = self.zs_dict[level]
            if len(zs_list) < 2:
                continue
            pre = zs_list[-2]
            cur = zs_list[-1]
            if pre.direction != cur.direction:
                continue

            if min(pre.high, cur.high) > max(pre.low, cur.low):  # 存在接触
                zs = copy(pre)
                zs.expand(cur)
                expand_res.append(zs)
        for zs in expand_res:
            self.add_zs(zs)

    def sz_stretch(self):
        """
        中枢延伸指中枢没有结束之前，可以继续上下波动，这种情况下，所有围绕走势中枢产生的前后两个次级波动都必须至少有一个触及走势中枢的区间。另外要注意，一旦中枢延伸出现9段，中枢就会升级。
        :return:
        """
        if self.cur_zs is None or not self.enable_stretch:
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
