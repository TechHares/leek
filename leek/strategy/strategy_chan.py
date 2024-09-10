#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 20:18
# @Author  : shenglin.li
# @File    : strategy_chan.py
# @Software: PyCharm
from leek.strategy import BaseStrategy


class ChanStrategy(BaseStrategy):
    verbose_name = "缠论V1"

    """
    缠论：禅中说缠理论实现
    参考文献地址： http://www.fxgan.com/chan_fenlei/index.htm#@
                 https://www.bilibili.com/read/cv16235114/
                 https://github.com/DYLANFREE/huangjun.work/blob/master/README.md
                 https://xueqiu.com/1468953003/78447616
    
    """

    def __init__(self):
        ...

    def _calculate(self):
        ...

    def handle(self):
        self._calculate()


if __name__ == '__main__':
    pass
