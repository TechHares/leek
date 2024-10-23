#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/10/21 19:09
# @Author  : shenglin.li
# @File    : de_mark.py
# @Software: PyCharm
"""
DeMark 系列指标
"""
from collections import deque

from leek.common import G
from leek.models.xg import data_process
from leek.t.ma import MA
from leek.t.t import T
from leek.trade.trade import PositionSide


class DeMarker(T):
    """
    DeMarker 震荡指标
    结果很跳跃，难以应用
    """

    def __init__(self, window=14, max_cache=100):
        T.__init__(self, max_cache)
        self.d_mmax = MA(window=window)
        self.d_mmin = MA(window=window)
        self.pre = None

    def update(self, data):
        de_mark = None
        try:
            if self.pre is None:
                return de_mark
            de_mmax = max(data.high - self.pre.high, 0)
            de_mmin = max(self.pre.low - data.low, 0)
            sma_max = self.d_mmax.update(G(close=de_mmax, finish=data.finish))
            sma_min = self.d_mmax.update(G(close=de_mmin, finish=data.finish))
            if sma_max is None or sma_min is None:
                return de_mark
            if sma_max + sma_min > 0:
                de_mark = int(sma_max / (sma_max + sma_min) * 100)
            else:
                de_mark = 50
            return de_mark
        finally:
            if data.finish == 1:
                self.pre = data
                self.cache.append(de_mark)

class TDSequence(T):
    """
    Tom Demark Sequential 9（TDS 9）

    Demark Sequential包含两个主要部分：Set up 和 Count down,下面以买入信号为例进行说明，卖出信号则相反。

    Set up: 要求有九个连续交易日的收盘价，每一个都低于其相对应的四个交易日前的收盘价。一个完美的Set up最好是第8或第9个交易日的最低价高于第6和第7个交易日的最低价。
    由一系列同一趋势方向的K线组成，根据其相邻间隔依次上涨或下跌的K线开始计数，如果某一根K线的收盘价违反计数规则，则重新从1开始计数，一般最多计数为9，也可能会出现13甚至以上的数字。


    Count Down: Set up完成后开始计数，每当某日收盘价低于其两天前的最低价时计数增加1 （可以不连续），直到计数增加到13。一个完美的count down最好是第十三个计数日的最低价不低于第8个计数日的收盘价。
    当启动序列计数达到9之后，倒数计数开始，同样是延续前一启动序列的方向，不同的是，如果倒数序列被打断，则不重新计数，直到下一个达到9的启动序列出现之后。

    买入点：较为激进的买入点是计数一完成就进入市场。第13个计数日常常是趋势的反转点。较为保守的买入点是等待count down完成后出现反转的信号，即某日的最低价不低于其4个交易日之前的收盘价。（完美的Count Down在第13个计数日就满足了这一反转信号）
    在启动序列当中，连续下跌达到9以上的序列，我们可以称其为一个买入结构，表示下跌趋势极有可能在不久之后衰竭。
    如果启动序列计数超过13，则表示其为一个强化的买入结构。

    取消计数：如果在Count Down尚未完成之前出现以下情况就应取消计数：1）有一个收盘价超过Set up阶段各日中的最高价；2）出现一个相反的Set up，如在买入的Count down过程中出现一个卖出的Set up; 3）出现新的一个同方向的Set up，在这种情况下新的买入Set up优先，一旦完成则重新开始计数。
    在启动序列当中，连续上涨达到9以上的序列，我们可以称其为一个卖出结构，表示上涨趋势极有可能在不久之后衰竭。
    如果启动序列计数超过13，则表示其为一个强化的卖出结构。

    止损点：一个成功的Set up和Count down完成后仍然有10%到30%的概率出现反转失败，止损点的设立很重要。首先找到Count Down阶段位置最低的一个price bar，以此price bar的最低价减去该日最高价（或前日收盘价，取其中较高一个）和最低价的差价，则此价格为止损点价格。

    支撑与压力线:
    我们一般会在某一启动序列的第9根K线收盘价的地方绘制支撑压力线。当K线价格在其下方运行时，该线表示压力；当K线价格在其上方运行时，该线表示支撑。

    买卖点的选择:
    我们一般会在一个买入结构或卖出结构完成时选择介入市场进行操作。

    激进的交易方式:
    激进的交易者会在某个计数达到9的序列出现之后立刻入场。但计数达到9并不能保证当前趋势一定会立即结束，此种交易方法过为冒进。

    保守的交易方式:
    保守的交易者应当在某一结构完成之后的下一根K线进行介入，并在支撑阻力位附近设置止损。或者只在计数达到13的加强结构之后进行交易。
    """

    def __init__(self, demark_len=9, setup_bias=4, countdown_bias=2, reverse_bias=4, max_countdown=13,
                 perfect_set_up=True, perfect_countdown=False, max_cache=100):
        assert demark_len >= 4
        assert not perfect_countdown or (perfect_countdown and max_countdown > 9)
        T.__init__(self, max_cache)
        self.demark_len = demark_len
        self.setup_bias = setup_bias
        self.countdown_bias = countdown_bias
        self.reverse_bias = reverse_bias
        self.max_countdown = max_countdown
        self.perfect_set_up = perfect_set_up
        self.perfect_countdown = perfect_countdown

        self.q = deque(maxlen=max(demark_len + setup_bias, countdown_bias + max_countdown) + 2)

        self.setup_direction = None
        self.td_line = None
        self.break_line = None
        self.eight_count_close = None
        self.countdown_peak_bar = None
        self.countdown = 0

    def __copy__(self):
        copy = TDSequence(demark_len=self.demark_len, setup_bias=self.setup_bias, reverse_bias = self.reverse_bias,
                          countdown_bias=self.countdown_bias,
                          max_countdown=self.max_countdown, perfect_countdown=self.perfect_countdown,
                          perfect_set_up=self.perfect_set_up, max_cache=self.cache.maxlen)

        copy.q = self.q.copy()
        copy.cache = self.cache.copy()
        copy.setup_direction = self.setup_direction
        copy.td_line = self.td_line
        copy.break_line = self.break_line
        copy.eight_count_close = self.eight_count_close
        copy.countdown = self.countdown
        copy.countdown_peak_bar = self.countdown_peak_bar
        return copy

    def update(self, data):
        res = None
        try:
            if data.finish == 0:
                copy = self.__copy__()
                copy.q.append(data)
                if not copy._setup():
                    copy._count_down()
                res = copy
            else:
                self.q.append(data)
                if not self._setup():
                    self._count_down()
                res = self
            return res
        finally:
            ...

    def last(self, n=100):
        raise NotImplementedError()

    def _reset(self):
        self.countdown = 0
        self.setup_direction = None
        self.countdown_peak_bar = None
        self.td_line = None
        self.break_line = None
        self.eight_count_close = None

    def _count_down(self):
        if self.setup_direction is None:
            return

        if abs(self.countdown) > self.max_countdown:
            return
        lst = list(self.q)
        data = lst[-1]
        if self.setup_direction.is_long:
            if self.countdown_peak_bar is None or data.low < self.countdown_peak_bar.low:
                self.countdown_peak_bar = data
        else:
            if self.countdown_peak_bar is None or data.high > self.countdown_peak_bar.high:
                self.countdown_peak_bar = data


        if (self.setup_direction.is_long and data.close >= self.break_line) or (
                self.setup_direction.is_short and data.close <= self.break_line):
            self._reset()
            return

        if len(lst) < self.countdown_bias + 1:
            return

        if abs(self.countdown) == self.max_countdown:
            if self._check_reversed():
                self.countdown *= 2
            return

        if self.setup_direction.is_long and data.close < lst[-1-self.countdown_bias].low:
            if self.perfect_countdown and abs(self.countdown) == self.max_countdown - 1:
                if data.low <= self.eight_count_close:
                    return
            self.countdown -= 1
            if self.countdown == -8:
                self.eight_count_close = data.close
        if self.setup_direction.is_short and data.close >= lst[-1-self.countdown_bias].high:
            if self.perfect_countdown and self.countdown == self.max_countdown - 1:
                if data.high >= self.eight_count_close:
                    return
            self.countdown += 1
            if self.countdown == 8:
                self.eight_count_close = data.close
        if abs(self.countdown) == self.max_countdown and self._check_reversed():
            self.countdown *= 2

    def _check_reversed(self):
        lst = list(self.q)
        if self.setup_direction.is_long:
            return len(lst) > self.reverse_bias+1 and lst[-1].low >= lst[-1-self.reverse_bias].close
        else:
            return len(lst) > self.reverse_bias+1 and lst[-1].high <= lst[-1-self.reverse_bias].close


    def _setup(self):
        if len(self.q) < self.demark_len + self.setup_bias:
            return False

        lst = list(self.q)
        if all([lst[self.setup_bias+i].close < lst[i].close for i in range(self.demark_len)]):
            if self.perfect_set_up and max(lst[-1].low, lst[-2].low) <= max(lst[-3].low, lst[-4].low):
                return False
            self.countdown = 0
            self.setup_direction = PositionSide.LONG
            self.countdown_peak_bar = lst[-1]
            self.td_line = lst[self.setup_bias].high
            self.break_line = max([x.high for x in lst[self.setup_bias:]])
            return True
        if all([lst[self.setup_bias+i].close > lst[i].close for i in range(self.demark_len)]):
            if self.perfect_set_up and min(lst[-1].high, lst[-2].high) >= min(lst[-3].high, lst[-4].high):
                return False
            self.countdown = 0
            self.setup_direction = PositionSide.SHORT
            self.td_line = lst[self.setup_bias].low
            self.countdown_peak_bar = lst[-1]
            self.break_line = min([x.low for x in lst[self.setup_bias:]])
            return True
        return False


class TDSequenceV2(T):
    """
    一、TD序列的构成
    TD序列包括两部分，一是TD结构，一是TD计数。以下均以下跌买入为例，来说明这两部分，下跌时出现的TD结构，称之为TD买入结构。

    1.   TD买入结构是这样形成的：
    （1）首先，要出现熊市价格反转，或称之为上涨转下跌。为了形成熊市价格反转，要求至少有六根K线，其中第五根K线的收盘价比第一根K线的收盘价高，第六根K线的收盘价，比第二根K线的收盘价低，那么就形成了熊市价格反转。这第六根K线，同时也是所谓的TD买入结构的第一根K线。

    （2）其次，当连续出现九根K线，并且这些K线的收盘价都比各自前面的第四根K线的收盘价低时，我们就说，形成了TD买入结构。请记住，必须是连续九根K线。如果出现中断，就必须重新开始构建。也就是重新寻找熊市价格反转，以及其后的TD买入结构。

    （3）TD买入结构并不限定只有九根K线，只要满足上述条件，可以一直延续。书中提到的TD买入结构最多有十八根K线。是否有更多的可能，书中并没有提到，我在上证指数运用该指标时，暂时没有发现超过18根的情况。

    （4）TD买入结构的第一根K线的最高价，也就是TD买入结构趋势阻力线，简称趋势阻力线。对应的，TD卖出结构的第一根K线的最低价，就是TD卖出结构趋势支撑线，简称趋势支撑线。

    2. TD买入计数
    （1）当TD买入结构形成之后，就开始进行TD买入计数。

    （2）当TD买入结构之后的K线（包括构成TD买入结构的第九根K线），满足收盘价小于等于它前面第二根K线（注：并非TD买入计数里的第二根K线，而是当前K线向前数第二根K线）的最低价时，就将它的计数加1。TD买入计数的最大值是13。

    （3）当TD买入计数达到12时，如果其后的K线满足计数条件，即收盘价小于等于它前面第二根K线的最低价，同时还要满足条件二，即它的最低价要小于等于计数8所对应K线的收盘价，此时这根K线计数为13。如果K线只满足计数条件，但是不满足条件二，那么这根K线就不能计数为13，在显示时只显示一个“+”。

    （4）TD买入计数可以是不连续的，也就是当某些K线不满足计数条件时，计数暂时中断。当再次遇到满足计数条件的K线时，继续前面的计数。

    （5）在TD计数过程中，如果出现TD卖出结构，则取消计数；
    （6）在TD计数过程中，如果出现K线的实际最低价，高于之前的TD买入结构趋势阻力线时，则取消计数。
    注：实际最低价指当前K线的最低价与其前一根K线的收盘价两者之间较低的价格。
    实际最高价指当前K线的最高价与其前一根K线的收盘价两者之间较高的价格。
    （7）如果出现连续的TD买入结构，即两个TD买入结构之间没有牛市价格反转，也没有TD卖出结构出现，则有可能形成两个TD买入计数嵌套的情况。其中，又有三种情况需要特殊处理：

    1）如果TD买入结构2的真实波幅大于等于TD买入结构1的真实波幅，但是又不超过其1.618倍，则TD买入计数1取消，保留TD买入计数2。

    2）如果TD买入结构2的收盘区间在TD买入结构1的真实区间（即真实波幅）之内，并且TD买入结构2的价格极值也在TD买入结构1的真实区间之内，那么TD买入计数2取消，保留TD买入计数1。

    3)如果TD买入计数1尚未结束，又出现了TD买入结构2，并且它延伸到18根K线，那么TD买入计数1的计数13出现时，不显示计数13，而显示字符“R”，表示循环计数，同时说明下跌趋势非常强列。

    注：连续两个TD买入结构，前一个称为TD买入结构1，相应的TD买入计数称为TD买入计数1；后一个称为TD买入结构2。相应的TD买入计数称为TD买入计数2.
    注：TD买入结构的真实波幅=TD买入结构的实际最高价-TD买入结构的实际最低价

    二、TD序列的使用
    1. TD买入结构的使用
    （1）买入条件
    1）TD买入结构的第八根K线或者第九根K线，或者其随其后的某根K线的最低价，小于等于第六根K线和第七根K线的最低价。
    2）TD买入结构内的任何一根K线的收盘价，都要在之前的TD卖出结构趋势支撑线之上。
    3）TD买入结构的第九根K线，要非常靠近之前的TD卖出结构趋势支撑线

    （2）期望值
    1）TD买入结构的实际最高价
    注：TD买入结构的实际最高价，指TD买入结构中所有K线的实际最高价中的最大值。

    （3）止损价位
    1)找到TD买入结构的实际最低价所对应的K线；
    注：TD买入结构的实际最低价，指TD买入结构中所有K线的实际最低价中的最小值。
    2）将该K线的实际最低价减去其真实波幅，就得到止损价位。
    注：真实波幅=|最高价-最低价|与|最高价-昨收|以及|昨收-最低价|三者之间的最大值。

    （4）建议
    TD买入结构的第九根K线的收盘价，满足其与目标价为的价差，是其与止损位的价差的1.5倍以上时，才进行交易。

    2. TD买入计数的使用
    （1）买入
    1）在计数13这根K线的收盘价入场（积极策略），或者
    2）在计数13之后，出现熊市价格反转时入场（保守策略），或者
    3）出现TD伪装买入信号时买入，或者
    . 当前K线的收盘价小于前一根K线的收盘价
    . 当前K线的收盘价大于当前K线的开盘价
    . 当前K线的最低价小于之前第二根K线的最低价

    4）出现TD马跳买入信号时买入，或者
    .当前K线的开盘价，必须小于前一根K线的开盘价和收盘价
    .随后的市场价格应该大于前一根K线的开盘价和收盘价

    5）出现TD马胜买入信号时买入，或者
    .当前K线必须包含于前一根K线之内，即它的开盘价与收盘价区间，在前一根K线的开盘价和收盘价区间内
    .当前K线的收盘价必须大于前一根K线的收盘价

    6）出现TD开盘买入信号时买入，或者
    .当前K线的开盘价小于前一根K线的最低价
    .随后的市场价格应该大于前一根K线的最低价

    7）出现TD陷阱买入信号时买入
    .当前K线的开盘价，在前一根K线的区间内（指开盘价与收盘价形成的区间）
    .随后的市场价格必须向上突破前一根K线的区间

    （2）止损价位
    1）找到TD计数的实际最低价所对应的K线
    2）计算该K线的实际最高价与实际最低价之差
    3）从该K线的实际最低价中减去上述差值，即得到止损价位

    三、TD序列的有关问题
    1、如何确认TD买入计数的止损价位被触发？
    假设K线X跌破止损价位，那么如下四个条件满足，则止损价位被触发：
    （1）K线X的收盘价低于止损价位
    （2）K线X-1的收盘价大于K线X-2的收盘价
    （3）K线X+1的是低开
    （4）K线X+1的最低价比开盘价低一个交易单位
    这是德马克建议的止损触发，实际交易中，最好是跌破止损价位就离场，而不要坐等其他条件成立。

    2、TD序列适合中国股市吗？
    根据作者意见，TD序列适应于任何市场，任何时间周期。参考本文开头部分的链接，可以见到德马克是如何在12月4日发出股市见底判断的。

    3、TD序列是如何发现的？
    德马克没有解释，但是从TD序列的构成来看，它与一周交易五天，斐波纳契数字8,13都有关联，可能这也是原创者的出发点之一吧。虽然很重要的数字九并不在其列。

    注：TD序列的问题并不都来自书。

    五、TD-积极序列
    TD-积极序列与TD序列基本类似，只是在TD计数时更激进一些。具体来说，就是TD序列中的在判断TD计数条件时，比较的是当前K线X的收盘价，与K线X-2的最低价。而在TD积极序列中，只有当K线X的最低价小于K线X-2的最低价时，才符合计数要求。因此，TD-积极序列总是先于TD序列产生买入信号或卖出信号。
    """
    def __init__(self):
        T.__init__(self, 0)

    def update(self, data):
        ...

class TDCombo(T):
    """
    TD组合与TD序列非常类似，差别也只在于TD组合的计数条件与TD序列的计数条件不同。TD组合的计数条件，有宽松版本和严格版本两种。
    1、TD组合的严格计数条件
    （1）K线X的收盘价，要求小于K线X-2的最低价；
    （2）K线X的最低价，要求小于K线X-1的最低价；
    （3）K线X的收盘价，要求小于K线X-1的收盘价；
    （4）K线X的收盘价，要求小于前一个计数K线的收盘价。
    注：前一个计数K线，指符合计数条件的K线，而不是当前K线的前一根K线。

    2、TD组合的宽松条件
    （1）计数1～10的K线，要求符合严格计数条件；
    （2）计数11、12、13的K线，只需要满足收盘价一个比一个低即可。

    3、TD组合的买入操作
    （1）TD组合计数完成之后，
    （2）等待出现TD价格反转时，就可以进行买入操作。这样就避开了TD组合循环的风险。
    注：与上述情况相反的，就是TD组合的卖出操作，

    4、TD组合的离场条件
    对于买入操作的离场设置是，将TD组合计数的实际最低价减去TD组合计数的真实波幅，就得到止损价位。
    """

    def __init__(self):
        T.__init__(self, 0)

    def update(self, data):
        ...

if __name__ == '__main__':
    pass
