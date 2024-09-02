#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/8/28 11:10
# @Author  : shenglin.li
# @File    : bsp.py
# @Software: PyCharm
from leek.t.chan.comm import ChanUnion, mark_data
from leek.t.chan.k import ChanK
from leek.t.chan.zs import ChanZS


class ChanBSPoint:
    """
    买卖点计算
    """
    def __init__(self):
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
        ...

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
        ...

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
        if zs.out_ele is not None and zs.out_ele.next == chan:
            if chan.is_up and k.high < zs.down_line:
                self.s3.append(k)

            if not chan.is_up and k.low > zs.up_line:
                self.b3.append(k)

    def mark_data(self):
        for b1 in self.b1:
            mark_data(b1.klines[-1], 'buy_point', "1b")
        for b2 in self.b2:
            mark_data(b2.klines[-1], 'buy_point', "2b")
        for b3 in self.b3:
            if b3 in self.b2:
                mark_data(b3.klines[-1], 'buy_point', "2b+3b")
            else:
                mark_data(b3.klines[-1], 'buy_point', "3b")
        for s1 in self.s1:
            mark_data(s1.klines[-1], 'sell_point', "1s")
        for s2 in self.s2:
            mark_data(s2.klines[-1], 'sell_point', "2s")
        for s3 in self.s3:
            if s3 in self.s2:
                mark_data(s3.klines[-1], 'sell_point', "2s+3s")
            else:
                mark_data(s3.klines[-1], 'sell_point', "3s")


if __name__ == '__main__':
    pass
