#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/28 17:17
# @Author  : shenglin.li
# @File    : portfolio.py
# @Software: PyCharm
"""
订单管理
风险管理
规模管理
"""

"""
仓位管理方式:
    假设资金为 Assest，VirtualRate 为动态管理系数，即根据不同的仓位水平设定不同的保证金规模使用情况，波动情况使用 ATR 指标来代替，开仓时的初始止损幅
    度为InitialStopLoss，N 为使用固定波幅法时的风险敞口，Rate 为使用固定百分比法时的参数，特定品种的合约乘数为 Lever，固定波幅法和固定百分比法仓位
    管理的公式如下：
        固定波幅法： Hands =  VirtualRate * Assest * N / ATR / Lever
        固定百分比法：Hands =  VirtualRate * Assest * Rate / InitialStopLoss / Lever
    可见在每次建仓时，对于固定百分比法，损失的百分比是固定的，对于固定波幅法，希望行情波动对净值的影响是固定的。
    当止损使用一定的 ATR 比例时，使用固定波幅仓位管理方法更合理，当使用一定的技术止损点位时，使用固定百分比仓位管理方法更合理。
"""

"""
风险管理:
        任何策略的净值表现均可能会阶段性的连续回撤，造成回撤的原因有很多，如行情的长期震荡，波动特性发生变化，毛刺过多等等。这里探讨一种对策略暂停运行的量化判断逻辑。
        首先需要分清仓位管理模块和开平仓择时模块的定位是不同的，开平仓择时的目的是提供一个长期来看正收益的时机判断，而仓位管理则如何通过仓位的控制更好的保证这种收益，
    当开平仓择时已经出现问题的情况下，仓位管理并不能从根本上进行改善。其次，策略暂停模块的主要目的是控制风险，在一些情况下，若不暂停运行策略，单个策略的净值也会慢
    慢恢复正常，另外一方面策略暂停模块也会导致部分“错杀”的可能。为了把注意力放在开平仓择时，我们监测开平仓仅一手条件下的策略净值表现。使用类似布林线的思路，根据策
    略过去一段时间的均值与方差，假设均值回溯期为 MoniterLen，方差参数为 MoniterB，构建一条仅向上跟随不向下波动的线策略暂停线。当策略净值曲线跌破策略停止线时，
    暂停策略运行，同时设置交叉位置为策略重启点，当策略净值曲线重新回到策略重启点时，重新启动策略运行。因趋势交易的单次亏损是有限的，所以仅当空仓时跌破策略停止线后才
    暂停策略运行，趋势交易的单次盈利可能较大，为了避免错过大幅趋势行情，当策略暂停后模拟交易持仓时回到策略重启点后，第二个交易日即真实买入开仓。当策略被暂停又重启后，
    暂设新的策略停止线为过去 MoniterLen 个交易日的策略净值低点。
        经过分析，参数 MoniterLen 若过短、MoniterB 过小，会频繁的导致策略暂停运行、重启运行，陷入恶性循环。另外，因为趋势类策略往往有一定的空仓时间，若参数 MoniterLen，
    会导致策略停止线与策略净值曲线贴合过紧，净值曲线稍一波动就会触发策略停止，因为 MoniterLen 和 MoniterB 均需要较大，给予策略净值曲线一定的波动范围。
"""
if __name__ == '__main__':
    pass
