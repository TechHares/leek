#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/28 11:10
# @Author  : shenglin.li
# @File    : bsp.py
# @Software: PyCharm
from decimal import Decimal

from django.template.defaultfilters import length

from leek.t.chan.comm import ChanUnion, mark_data
from leek.t.chan.k import ChanK
from leek.t.chan.zs import ChanZS


class ChanBSPoint:
    """
    买卖点计算
    """
    def __init__(self, b1_zs_num=1, max_interval_k = 2):
        self.max_interval_k = max_interval_k
        self.b1_zs_num = b1_zs_num
        self.b1 = []
        self.s1 = []

        self.b2 = []
        self.s2 = []

        self.b3 = []
        self.s3 = []

    def calc_bsp(self, zs: ChanZS, chan: ChanUnion, k: ChanK):
        self._calc_first_point(zs, chan, k)
        self._calc_second_point(zs, chan, k)
        self._calc_third_point(zs, chan, k)

    def _calc_first_point(self, zs: ChanZS, chan: ChanUnion, k: ChanK):
        """
        任一背驰都必然制造某级别的买卖点，任一级别的买卖点都必然源自某级别走势的背驰。
        第一类买点：某级别下跌趋势中，一个次级别走势类型向下跌破最后一个走势中枢后形成的背驰点

        强度：
        1，线段即可能构成背驰，但此类背驰，1买力度是最弱的，甚至可以说，不是1买，如果转折定义为小转大
        2，有一个中枢的底背，就是盘背，有可能构成1买，力度值得怀疑。主要用在大级别上。
        3，两个中枢的趋势背驰，是大部分，构成1买通常力度较强，1买后形成反转的概率很大了
        4，三个中枢的趋势背驰，这不是很多了，1买转折力度超强，但不容易找到。

        止损：
            跌破一买低点/升破一卖高点

        优点：（1）进入段a利润较大；（2）持仓成本占据有利位置。
        缺点：（1）反转点的判断容易出现错误；（2）进场后反弹的高度不确定；（3）进场后并不能马上开始上涨，可能进入盘整；
        :param k:
        :return:
        """
        if zs is None or chan.size > self.max_interval_k or not zs.is_satisfy:
            return

        if zs.out_ele != chan and ((not chan.is_finish and zs.element_list[-1] != chan) or (chan.is_finish and zs.element_list[-1] != chan.pre)):
            return
        if zs.direction == chan.direction:
            return

        chan = chan.pre
        if self.b1_zs_num > 1:
            def check_zs(_zs: ChanZS):
                return _zs.pre is not None and _zs.pre.direction == _zs.direction
            n = self.b1_zs_num

            cur_zs = zs
            while n > 1 and check_zs(cur_zs):
                n -= 1
                cur_zs = cur_zs.pre
            if n > 1: # 没有方向相同的同级别n个中枢，1类买卖点无法成立
                return

        # 背驰采用直接判断法， 比较两中枢走出段的长度和斜率
        length1 = chan.high - zs.up_line if chan.is_up else zs.down_line - chan.low
        if length1 < (zs.up_line - zs.down_line) / 2:  # 长度太短
            return
        length2 = zs.down_line - zs.into_ele.low if chan.is_up else zs.into_ele.high - zs.up_line
        # length1 = chan.high - chan.low
        # length2 = zs.into_ele.high - zs.into_ele.low
        if length1 > length2 * Decimal("1.3"):  # 长度反差
            return
        if length1 / length2 > Decimal("0.9") and ((chan.high - chan.low) / chan.size > (zs.into_ele.high - zs.into_ele.low) / zs.into_ele.size): # 长度微短但斜率加重
            return

        if not chan.is_up and chan.low <= zs.low:
            self.b1.append(k)
        if chan.is_up and chan.high >= zs.high:
            self.s1.append(k)

    def _calc_second_point(self, zs: ChanZS, chan: ChanUnion, k: ChanK):
        """
        第二类买点：某级别中，第一类买点的次级别上涨结束后再次下跌的那个次级别走势的结束点

        强度：
        1，2-3重叠的最强
        2，2买在中枢内部形成，强度还可以，可以继续操盘
        3，2买在中枢之下形成，强度值得怀疑，通常应该考虑走完向上的次级别，应该换股
        4，中继性2买，即小转大形成，力度值得怀疑。等于中途刹车一次后前行，勉强可以继续，总之不是好事了。

        止损：
            1.跌破一买低点/升破一卖高点
            2.走完次级别走势之后 跌破二买低点/升破二卖高点

        优点：（1）成功率较高；（2）利润多少有参考；（3）买在三买前的最后一个二买，利润较大。
        缺点：（1）中枢操作过程中，存在利润全部抹掉的可能；（2）窄幅震荡的中枢利润一般较小，很难出现意外暴涨的收获。
        :param k:
        :return:
        """
        # 使用bsp1的计算结果
        if chan.pre is None or chan.pre.pre is None or chan.size > self.max_interval_k:
            return
        chan = chan.pre
        if chan.is_up and chan.high > chan.pre.high:
            return
        if not chan.is_up and chan.low < chan.pre.low:
            return

        bsp1 = None
        lst = None
        if chan.is_up and len(self.s1) > 0:
            bsp1 = self.s1[-1]
            lst = self.s2
        if not chan.is_up and len(self.b1) > 0:
            bsp1 = self.b1[-1]
            lst = self.b2
        if bsp1 is None:
            return

        if (chan.pre.start_timestamp <= bsp1.start_timestamp <= chan.pre.end_timestamp and
                chan.pre.start_timestamp <= bsp1.end_timestamp <= chan.pre.end_timestamp):
            lst.append(k)


    def _calc_third_point(self, zs: ChanZS, chan: ChanUnion, k: ChanK):
        """
        第三类买卖点定理：
            一个次级别走势类型向上离开缠中说禅走势中枢，必须是第一次创新高，然后以一个次级别走势类型回试，其低点不跌破 ZG，则构成第三类买点；
            一个次级别走势类型向下离开缠中说禅走势中枢，必须是第一次创新低，然后以一个次级别走势类型回抽，其高点不升破 ZD，则构成第三类卖点

        1，次级别盘整回试的最强，特别是次级别水平横盘，窄幅缩量震荡
        2，中枢简单的，也比较强，基本属于正常的三买
        3，产生复杂中枢震荡后，形成的三买，力度值得怀疑，次级别向上后，如果力度不足，基本就要完蛋了。
        4，第二个中枢以后的三买，可以操作，便要十分小心趋势顶背驰了

        止损：
            1.跌/涨回中枢
            2.走完次级别走势之后 跌破三买低点/升破三卖高点

        优点：（1）三买一旦成功，往往后面上涨快速，不用等待，且利润较大。
        缺点：（1）三买后很多时候会出现一卖；
        :param k:
        :return:
        """
        if zs is None or chan.pre is None or chan.size > self.max_interval_k:
            return
        chan = chan.pre
        if zs.direction == chan.direction:
            return
        if chan.pre is None or (chan.pre not in zs.element_list and chan.pre != zs.out_ele):
            return

        if zs.is_up and (chan.high < zs.high or chan.low <= zs.up_line):
            return
        if not zs.is_up and (chan.low > zs.low or chan.high >= zs.down_line):
            return
        if chan.is_up:
            self.s3.append(k)
        else:
            self.b3.append(k)

    def mark_data(self, mark=""):
        for b1 in self.b1:
            mark_data(b1.klines[-1], f'buy_point{mark}', "1b")
        for b2 in self.b2:
            mark_data(b2.klines[-1], f'buy_point{mark}', "2b")
        for b3 in self.b3:
            if b3 in self.b2:
                mark_data(b3.klines[-1], f'buy_point{mark}', "2b+3b")
            else:
                mark_data(b3.klines[-1], f'buy_point{mark}', "3b")
        for s1 in self.s1:
            mark_data(s1.klines[-1], f'sell_point{mark}', "1s")
        for s2 in self.s2:
            mark_data(s2.klines[-1], f'sell_point{mark}', "2s")
        for s3 in self.s3:
            if s3 in self.s2:
                mark_data(s3.klines[-1], f'sell_point{mark}', "2s+3s")
            else:
                mark_data(s3.klines[-1], f'sell_point{mark}', "3s")


if __name__ == '__main__':
    pass
