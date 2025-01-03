量韭
===============
韭菜量化平台, 基于Python的事件驱动quant平台, 提供从数据获取到交易的整套流程, 以及交易的回测, 策略评估

[![leek](https://img.shields.io/github/license/li-shenglin/leek.svg)](https://github.com/li-shenglin/leek)
[![leek](https://img.shields.io/github/release/li-shenglin/leek)](https://github.com/li-shenglin/leek)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)
![Pip Version](https://img.shields.io/badge/pip-2.24.2%2B-green.svg)
![Django Version](https://img.shields.io/badge/Django-4.2.13%2B-read.svg)
[![simpleui](https://img.shields.io/badge/developing%20with-Simpleui-2077ff.svg)](https://github.com/newpanjing/simpleui)

## 特色
1. 系统基于事件构建易于扩展策略或者其他组件
2. 丰富的指标和策略可供学习和研究
3. 表达式引擎支持自定义指标和特征，对代码不熟悉的同学友好
4. 模型训练、模型预测、模型评估全过程支持

## 快速开始
- [使用文档](docs/0-1.introduction.md)
- 讨论组：<a href="https://t.me/+lFHR-vTZ6Y1iZTU1">Telegram</a>

策略
--------------------

| 名称         | 是否支持     | 支持版本   | 简介 |
|:-----------|:---------|:-------|:---|
| 单标的单向网格    | &#10004; | v0.0.1 |    |
| 均值回归       | &#10004; | v0.0.2 |    |
| 布林带策略      | &#10004; | v0.0.2 |    |
| ATR+HA策略   | &#10004; | v0.0.3 |    |
| 双均线        | &#10004; | v0.0.4 |    |
| MACD均线     | &#10004; | v0.0.4 |    |
| 超级趋势       | &#10004; | v0.0.5 |    |
| 多数决策略      | &#10004; | v0.0.5 |    |
| 游龙一        | &#10004; | v0.0.5 |    |
| 海龟交易       | &#10004; | v0.0.6 |    |
| 海龟交易V1     | &#10004; | v0.0.6 |    |
| 海龟交易V2     | &#10004; | v0.0.6 |    |
| 海龟交易V3     | &#10004; | v0.0.6 |    |
| 道氏法则1      | &#10004; | v0.0.6 |    |
| 布林带策略V2    | &#10004; | v0.1.3 |    |
| RSI集成策略    | &#10004; | v0.1.3 |    |
| RSJ策略      | &#10004; | v0.1.3 |    |
| 均线(LLT)    | &#10004; | v0.1.3 |    |
| TD择时策略     | &#10004; | v0.1.4 |    |
| 希尔伯特变换择时策略 | &#10004; | v0.1.4 |    |
| RSI网格      | &#10004; | v0.1.4 |    |
| RSI网格V2    | &#10004; | v0.1.4 |    |
| 缠论         | &#10004; | v0.1.5 |    |
| MACD反转择时   | &#10004; | v0.1.5 |    |
| 游龙二(多指标组合) | &#10004; | v0.1.5 |    |
| TDS 策略     | &#10004; | v0.2.0 |    |
| 一目云图简单应用   | &#10004; | v0.3.0 |    |
| DMI简单应用    | &#10004; | v0.3.0 |    |
| CCI简单应用    | &#10004; | v0.4.0 |    |
| ...        | &#10008; | ...    |




[升级日志](docs/0-2.change_log.md)

版本说明： v(固定)x(涉架构升级).x(新增功能/策略/特性).x(BUG修复/功能优化)