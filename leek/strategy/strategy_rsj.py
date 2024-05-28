#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/17 19:21
# @Author  : shenglin.li
# @File    : strategy_rsj.py
# @Software: PyCharm
# from leek.strategy import BaseStrategy
# from leek.strategy.common.decision import STDecisionNode
# from leek.strategy.common.strategy_common import PositionRateManager, PositionDirectionManager
# from leek.trade.trade import PositionSide


# class RSJStrategy(PositionDirectionManager, PositionRateManager, BaseStrategy):
#     verbose_name = "高频波动率不对称性择时"
#
#     """
#     Bollerslev et al. (2019) 指出高频环境下的已实现方差不对称性 RSJ 具有显著的负溢价，而 Huang and Li (2019) 则指出隐含方差不对称性 IVA 有显著的正溢价。
#     二者的差异看似矛盾，但其实很容易理解：RSJ 是事后指标，而 IVA 是事前指标，反映拥有私有信息的投资者的预期。
#     这是截面因子，跟 VIX 无关。RSJ 有显著的负溢价，IVA 有显著的正溢价，所以做多 RSJ 低（IVA 高）的股票并做空 RSJ 高（IVA 低）的股票，据此构建低 RSJ（高 IVA）因子。
#     VA 类似于 RSJ，都是根据历史数据计算的已实现波动率，只是 RSJ 本身是基于日内高频数据
#
#
#     参考文献：
#         https://cicfconf.org/sites/default/files/paper_579.pdf
#         https://zhuanlan.zhihu.com/p/92747173
#         https://www.doc88.com/p-18039734259993.html?r=1
#     """


if __name__ == '__main__':
    pass
