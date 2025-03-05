#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/7 19:52
# @Author  : shenglin.li
# @File    : chan.py
# @Software: PyCharm
from leek.t.chan.bi import ChanBIManager
from leek.t.chan.dr import ChanDRManager
from leek.t.chan.enums import BiFXValidMethod
from leek.t.chan.k import ChanKManager
from leek.t.chan.seg import ChanSegmentManager
from leek.t.chan.zs import ChanZSManager
from leek.t.t import T


class Chan(T):
    def __init__(self, exclude_equal=False, zs_max_level=2, allow_similar_zs=True):
        """
        缠论：递归计算一次
        :param exclude_equal: 合并时是否排除相等的元素
        :param zs_max_level: 最大中枢级别
        :param allow_similar_zs: 是否允许类中枢
        """
        super().__init__()

        self.seg_manager = ChanSegmentManager(exclude_equal)
        self.zs_manager = ChanZSManager(max_level=zs_max_level, allow_similar_zs=allow_similar_zs)
        self.dr_manager = ChanDRManager()
        self.tmp_zs = None


    def update(self, data):
        seg = self.seg_manager.update(data)
        if seg:
            self.zs_manager.update(seg)
            for zs in self.zs_manager.zs_list:
                if self.tmp_zs is None or zs.idx >= self.tmp_zs.idx:
                    self.dr_manager.update(zs)
                    self.tmp_zs = zs
            if self.zs_manager.cur_zs:
                self.dr_manager.update(self.zs_manager.cur_zs)
                self.tmp_zs = self.zs_manager.cur_zs



if __name__ == '__main__':
    pass
