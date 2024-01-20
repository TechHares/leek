#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 21:32
# @Author  : shenglin.li
# @File    : evaluation.py
# @Software: PyCharm
from decimal import Decimal

import numpy as np


class Evaluation(object):
    def __init__(self):
        """
        策略评价
        自评：
        1.年化收益率
        2.累计收益率
        3.波动率
        4.夏普比率
        5.日度收益率
        6.最大回撤
        7.sortino比率
        8.下行风险
        9.最大回撤期内收益
        10.资本回报率
        11.信息比率
        12.负载率
        13.alpha
        14.beta
        15.R平方
        16.Treynor比率
        17.Calmar比率
        """
        self.value_list = []
        self.benchmark_list = []
        self.daily = 0
        self.fee = 0

        self.benchmark_arr = None
        self.value_arr = None

    def __getattribute__(self, name):
        def _get(_attr):
            return object.__getattribute__(self, _attr)

        def _set(_attr, v):
            return object.__setattr__(self, _attr, v)

        if name == "update_profit_data":
            if _get("value_arr") is not None:
                _set("value_arr", None)
                _set("benchmark_arr", None)
        elif name.startswith("calculate_"):
            if _get("value_arr") is None:
                _set("value_arr", np.array(_get("value_list")))
            if _get("benchmark_arr") is None:
                _set("benchmark_arr", np.array(_get("benchmark_list")))
            if len(_get("value_list")) == 0:
                def no_data(*args, **kwargs):
                    return "--"

                return no_data
        return _get(name)

    def update_profit_data(self, data):
        if "amount" not in data or not data["amount"] or data["amount"] <= 0:
            return

        if "benchmark_price" not in data or not data["benchmark_price"] or data["benchmark_price"] <= 0:
            return

        d = int(data["timestamp"] / (1000 * 60 * 60 * 24))
        if d < self.daily:
            return
        if d == self.daily:
            self.value_list[-1] = float(data["amount"])
            self.benchmark_list[-1] = float(data["benchmark_price"])
        else:
            self.value_list.append(float(data["amount"]))
            self.benchmark_list.append(float(data["benchmark_price"]))
            self.daily = d
        self.fee = float(data["fee"])

    def calculate_annualized_return(self, day_in_year=360):
        """
        :return: 年化收益率
        """
        return self.calculate_average_daily_return() * day_in_year

    def calculate_cumulative_return(self):
        """
        :return: 累计收益率
        """
        return (self.value_list[-1] - self.value_list[0]) / self.value_list[0]

    def calculate_volatility(self):
        """
        :return: 波动率
        """
        return np.std(np.diff(self.value_arr) / self.value_arr[:-1])

    def calculate_sharpe_ratio(self, risk_free_rate=0.03/365):
        """
        :return: 夏普比率
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        return (np.mean(daily_returns) - risk_free_rate) / np.std(daily_returns)

    def calculate_average_daily_return(self):
        """
        :return: 日度收益率
        """
        return np.mean(np.diff(self.value_arr) / self.value_arr[:-1])

    def calculate_max_drawdown(self):
        """
        :return: 最大回撤
        """
        # 计算每个时间点之前的峰值
        peak_values = np.maximum.accumulate(self.value_arr)
        # 计算每个时间点的回撤
        drawdowns = (self.value_arr - peak_values) / peak_values
        # 找到最大回撤
        return np.min(drawdowns)

    def calculate_sortino_ratio(self, risk_free_rate=0.03/365):
        """
        :return: sortino比率
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1] - risk_free_rate
        # 提取负收益
        negative_returns = daily_returns[daily_returns < 0]
        return (self.calculate_average_daily_return() - risk_free_rate) / np.std(negative_returns)

    def calculate_downside_risk(self, risk_free_rate=0.03/365):
        """
        :return: 下行风险
        """
        # 计算每日资产净值的日度收益率
        daily_returns = np.diff(self.value_arr) / self.value_arr[:-1] - risk_free_rate
        # 提取负收益
        negative_returns = daily_returns[daily_returns < 0]
        negative_returns_squared_sum = np.sum(negative_returns ** 2)

        # 计算观测期数
        n = len(self.value_arr)

        # 计算负收益的标准差，即下行风险
        return np.sqrt(negative_returns_squared_sum / n)

    def calculate_max_drawdown_return(self):
        """
        :return: 最大回撤期内收益
        """
        # 计算每个时间点之前的峰值
        peak_values = np.maximum.accumulate(self.value_arr)

        # 计算每个时间点的回撤
        drawdowns = (self.value_arr - peak_values) / peak_values
        # 找到最大回撤的开始和结束位置
        start_index = np.argmax(drawdowns == 0)  # 最大回撤开始位置
        end_index = np.argmax(drawdowns == np.min(drawdowns))  # 最大回撤结束位置
        # 计算最大回撤期间收益
        return (self.value_arr[end_index] - self.value_arr[start_index]) / self.value_arr[start_index]

    def calculate_capital_return(self):
        """
        :return: 资本回报率
        """
        return (self.value_list[-1] - self.value_list[0] - self.fee) / self.value_list[0]

    def calculate_information_ratio(self):
        """
        :return: 信息比率
        """
        # 计算每日收益
        portfolio_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        benchmark_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算每日超额收益
        excess_returns = portfolio_returns - benchmark_returns
        # 计算超额收益的平均值和标准差
        mean_excess_returns = np.mean(excess_returns)
        std_excess_returns = np.std(excess_returns)
        # 计算信息比率
        return mean_excess_returns / std_excess_returns

    def calculate_beta(self):
        """
        :return: 负载率
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算资产与市场的协方差矩阵
        covariance_matrix = np.cov(asset_returns, market_returns)
        # 提取资产与市场的协方差和市场的方差
        covariance_asset_market = covariance_matrix[0, 1]
        variance_market = covariance_matrix[1, 1]

        # 计算Beta
        return covariance_asset_market / variance_market

    def calculate_alpha(self, risk_free_rate=0.03/365):
        """
        :return: alpha
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算Alpha
        expected_market_return = risk_free_rate + self.calculate_beta() * (np.mean(market_returns) - risk_free_rate)
        actual_asset_return = np.mean(asset_returns)
        return actual_asset_return - expected_market_return

    def calculate_r_squared(self):
        """
        :return: R平方
        """
        # 计算每日资产（或投资组合）和市场的收益率
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        market_returns = np.diff(self.benchmark_arr) / self.benchmark_arr[:-1]
        # 计算残差平方和 rss
        residual_sum_of_squares = np.sum((asset_returns - market_returns) ** 2)

        # 计算总平方和
        total_sum_of_squares = np.sum((asset_returns - np.mean(asset_returns)) ** 2)

        # 计算R平方
        return 1 - (residual_sum_of_squares / total_sum_of_squares)

    def calculate_treynor_ratio(self, risk_free_rate=0.03/365):
        """
        :return: Treynor比率
        """
        # 假设有资产（或投资组合）和市场的每日收益率数据
        asset_returns = np.diff(self.value_arr) / self.value_arr[:-1]
        # 计算超额收益
        excess_returns = asset_returns - risk_free_rate
        # 计算Treynor比率
        return np.mean(excess_returns) / self.calculate_beta()

    def calculate_calmar_ratio(self, day_in_year=360):
        """
        :return: Calmar比率
        """
        return self.calculate_annualized_return(day_in_year) / self.calculate_max_drawdown()

    def calculate_statistics(self):
        return {
                "annualized_return": "%.2f%%" % (self.calculate_annualized_return() * 100),  # 年化收益率
                "cumulative_return": "%.2f%%" % (self.calculate_cumulative_return() * 100),  # 累计收益率
                "sharpe_ratio": self.calculate_sharpe_ratio(),  # 夏普比率
                "average_daily_return": "%.2f%%" % (self.calculate_average_daily_return() * 100),  # 日均收益率
                "volatility": self.calculate_volatility(),  # 波动率
                "maximum_drawdown": "%.2f%%" % (self.calculate_max_drawdown() * 100),  # 最大回撤
                "downside_risk": self.calculate_downside_risk(),  # 下行风险
                "sortino_ratio": self.calculate_sortino_ratio(),  # Sortino比率
                "maximum_drawdown_duration": "%.2f%%" % (self.calculate_max_drawdown_return() * 100),  # 最大回撤期内收益
                "capital_utilization": "%.2f%%" % (self.calculate_capital_return() * 100),  # 资本回报率
                "calmar_ratio": self.calculate_calmar_ratio(),  # calmar比率
                "alpha": self.calculate_alpha(),  # Alpha
                "beta": self.calculate_alpha(),  # Beta
                "r_squared": self.calculate_r_squared(),  # R-squared
                "information_ratio": self.calculate_information_ratio(),  # 信息比率
                "treynor_ratio": self.calculate_treynor_ratio(),  # Treynor比率
            }


if __name__ == '__main__':
    e = Evaluation()
    e.value_list = [Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'),
                    Decimal('1000.00'), Decimal('1000.00'), Decimal('1000.00'), Decimal('1002.959043'),
                    Decimal('1051.995213'), Decimal('1050.287060'), Decimal('1063.397923'), Decimal('1041.390242'),
                    Decimal('1048.714117'), Decimal('991.798849'), Decimal('976.531051'), Decimal('923.982121'),
                    Decimal('940.921246'), Decimal('927.656029'), Decimal('924.599458'), Decimal('937.894789'),
                    Decimal('936.258595'), Decimal('959.521660'), Decimal('948.846247'), Decimal('954.593002'),
                    Decimal('949.097197'), Decimal('915.836284'), Decimal('940.419346'), Decimal('956.505241'),
                    Decimal('942.110749'), Decimal('998.514271'), Decimal('950.899018'), Decimal('958.527898'),
                    Decimal('920.870341'), Decimal('925.748809'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008'),
                    Decimal('901.763008'), Decimal('901.763008'), Decimal('901.763008')]
    e.benchmark_list = [Decimal('1253.14'), Decimal('1265.80'), Decimal('1262.53'), Decimal('1262.90'),
                        Decimal('1323.30'), Decimal('1323.99'), Decimal('1332.77'), Decimal('1397.29'),
                        Decimal('1432.59'), Decimal('1540.52'), Decimal('1555.71'), Decimal('1578.93'),
                        Decimal('1593.01'), Decimal('1542.24'), Decimal('1532.53'), Decimal('1585.40'),
                        Decimal('1653.25'), Decimal('1657.66'), Decimal('1629.72'), Decimal('1622.12'),
                        Decimal('1534.24'), Decimal('1605.11'), Decimal('1600.87'), Decimal('1566.10'),
                        Decimal('1653.63'), Decimal('1565.92'), Decimal('1571.66'), Decimal('1581.62'),
                        Decimal('1673.66'), Decimal('1656.70'), Decimal('1686.00'), Decimal('1647.33'),
                        Decimal('1649.23'), Decimal('1656.53'), Decimal('1644.65'), Decimal('1623.87'),
                        Decimal('1508.40'), Decimal('1539.42'), Decimal('1510.99'), Decimal('1487.99'),
                        Decimal('1559.42'), Decimal('1663.99'), Decimal('1675.96'), Decimal('1676.55'),
                        Decimal('1689.77'), Decimal('1685.30'), Decimal('1700.77'), Decimal('1673.83'),
                        Decimal('1611.91'), Decimal('1650.28'), Decimal('1606.39'), Decimal('1600.73'),
                        Decimal('1639.17'), Decimal('1624.59'), Decimal('1630.29'), Decimal('1640.89'),
                        Decimal('1641.42'), Decimal('1561.19'), Decimal('1568.19'), Decimal('1568.65'),
                        Decimal('1564.25'), Decimal('1548.89'), Decimal('1559.89'), Decimal('1437.50'),
                        Decimal('1421.89'), Decimal('1458.42'), Decimal('1575.03'), Decimal('1683.22'),
                        Decimal('1714.83'), Decimal('1696.88'), Decimal('1660.61'), Decimal('1764.12'),
                        Decimal('1771.83'), Decimal('1823.33'), Decimal('1750.61'), Decimal('1801.44'),
                        Decimal('1737.50'), Decimal('1813.27'), Decimal('1746.01'), Decimal('1754.76'),
                        Decimal('1774.77'), Decimal('1705.43'), Decimal('1730.00'), Decimal('1786.16'),
                        Decimal('1776.72'), Decimal('1789.56'), Decimal('1823.32'), Decimal('1788.98'),
                        Decimal('1796.80'), Decimal('1873.00'), Decimal('1907.99'), Decimal('1867.46'),
                        Decimal('1864.56'), Decimal('1859.50'), Decimal('1837.74'), Decimal('1901.01'),
                        Decimal('1914.48'), Decimal('1912.78'), Decimal('1999.53'), Decimal('2099.59'),
                        Decimal('2104.77'), Decimal('2124.89'), Decimal('2099.68'), Decimal('2092.31'),
                        Decimal('1974.89'), Decimal('1953.45'), Decimal('1884.20'), Decimal('1874.34'),
                        Decimal('1874.34'), Decimal('1841.82'), Decimal('1868.31'), Decimal('1865.05'),
                        Decimal('1911.40'), Decimal('1891.12'), Decimal('1895.46'), Decimal('1925.45'),
                        Decimal('1831.22'), Decimal('1829.72'), Decimal('1905.39'), Decimal('1876.71'),
                        Decimal('1989.09'), Decimal('1881.32'), Decimal('1918.80'), Decimal('1834.39'),
                        Decimal('1844.11'), Decimal('1832.56'), Decimal('1790.46'), Decimal('1772.73'),
                        Decimal('1791.73'), Decimal('1806.64'), Decimal('1815.83'), Decimal('1825.45'),
                        Decimal('1823.83'), Decimal('1809.14'), Decimal('1809.43'), Decimal('1809.43'),
                        Decimal('1808.21'), Decimal('1813.62'), Decimal('1851.58'), Decimal('1798.51'),
                        Decimal('1803.40'), Decimal('1827.57'), Decimal('1830.92'), Decimal('1909.01'),
                        Decimal('1889.84'), Decimal('1905.04'), Decimal('1865.46'), Decimal('1859.82'),
                        Decimal('1904.20'), Decimal('1901.20'), Decimal('1901.29'), Decimal('1804.59'),
                        Decimal('1877.60'), Decimal('1840.50'), Decimal('1850.00'), Decimal('1836.50'),
                        Decimal('1836.50'), Decimal('1767.70'), Decimal('1741.08'), Decimal('1735.16'),
                        Decimal('1648.83'), Decimal('1647.36'), Decimal('1679.59'), Decimal('1724.80'),
                        Decimal('1735.60'), Decimal('1731.37'), Decimal('1791.37'), Decimal('1875.80'),
                        Decimal('1881.44'), Decimal('1906.38'), Decimal('1894.00'), Decimal('1902.11'),
                        Decimal('1852.33'), Decimal('1874.42'), Decimal('1874.42'), Decimal('1850.26'),
                        Decimal('1843.00'), Decimal('1920.80'), Decimal('1924.30'), Decimal('1967.50'),
                        Decimal('1955.46'), Decimal('1927.80'), Decimal('1888.80'), Decimal('1869.23'),
                        Decimal('1855.66'), Decimal('1868.92'), Decimal('1870.91'), Decimal('1870.37'),
                        Decimal('1886.86'), Decimal('1880.86'), Decimal('1902.84'), Decimal('1930.49'),
                        Decimal('1930.99'), Decimal('1911.93'), Decimal('1895.06'), Decimal('1910.31'),
                        Decimal('1883.85'), Decimal('1895.00'), Decimal('1888.33'), Decimal('1892.46'),
                        Decimal('1849.50'), Decimal('1861.28'), Decimal('1881.83'), Decimal('1867.89'),
                        Decimal('1872.13'), Decimal('1880.29'), Decimal('1874.86'), Decimal('1860.15'),
                        Decimal('1834.85'), Decimal('1835.18'), Decimal('1844.41'), Decimal('1828.00'),
                        Decimal('1835.32'), Decimal('1828.00'), Decimal('1829.52'), Decimal('1842.57'),
                        Decimal('1853.00'), Decimal('1849.59'), Decimal('1844.83'), Decimal('1848.85'),
                        Decimal('1847.64'), Decimal('1842.89'), Decimal('1829.46'), Decimal('1821.51'),
                        Decimal('1638.68'), Decimal('1663.13'), Decimal('1661.58'), Decimal('1676.67'),
                        Decimal('1664.81'), Decimal('1627.47'), Decimal('1642.49'), Decimal('1646.51'),
                        Decimal('1646.49'), Decimal('1651.80'), Decimal('1656.57'), Decimal('1649.18'),
                        Decimal('1726.69'), Decimal('1705.32'), Decimal('1669.24'), Decimal('1606.30'),
                        Decimal('1632.26'), Decimal('1634.87'), Decimal('1627.54'), Decimal('1635.90'),
                        Decimal('1615.53'), Decimal('1633.24'), Decimal('1635.91'), Decimal('1634.82'),
                        Decimal('1622.92'), Decimal('1560.30'), Decimal('1601.05'), Decimal('1605.73'),
                        Decimal('1617.99'), Decimal('1643.69'), Decimal('1636.26'), Decimal('1628.31'),
                        Decimal('1648.43'), Decimal('1653.84'), Decimal('1632.70'), Decimal('1584.86'),
                        Decimal('1593.29'), Decimal('1592.77'), Decimal('1589.88'), Decimal('1586.72'),
                        Decimal('1587.62'), Decimal('1594.66'), Decimal('1653.36'), Decimal('1667.41'),
                        Decimal('1669.14'), Decimal('1676.52'), Decimal('1691.11'), Decimal('1653.52'),
                        Decimal('1645.17'), Decimal('1612.31'), Decimal('1647.06'), Decimal('1633.63'),
                        Decimal('1634.37'), Decimal('1580.30'), Decimal('1556.19'), Decimal('1566.38'),
                        Decimal('1566.38'), Decimal('1548.48'), Decimal('1554.48'), Decimal('1552.96'),
                        Decimal('1552.96'), Decimal('1580.79'), Decimal('1556.13'), Decimal('1564.75'),
                        Decimal('1607.39'), Decimal('1633.81'), Decimal('1633.55'), Decimal('1711.59'),
                        Decimal('1786.64'), Decimal('1788.18'), Decimal('1804.99'), Decimal('1793.70'),
                        Decimal('1777.24'), Decimal('1790.05'), Decimal('1799.69'), Decimal('1813.05'),
                        Decimal('1793.02'), Decimal('1839.88'), Decimal('1815.04'), Decimal('1836.41'),
                        Decimal('1897.16'), Decimal('1891.85'), Decimal('1877.63'), Decimal('1887.24'),
                        Decimal('2133.15'), Decimal('2083.22'), Decimal('2057.75'), Decimal('2057.84'),
                        Decimal('2051.43'), Decimal('1980.87'), Decimal('2013.30'), Decimal('1969.46'), Decimal('1944'),
                        Decimal('1957.90'), Decimal('1978.02'), Decimal('2030.42'), Decimal('1969.36'),
                        Decimal('2059.71'), Decimal('2056.70'), Decimal('2078.19'), Decimal('2083.32'),
                        Decimal('2056.97'), Decimal('2024.32'), Decimal('2008.02'), Decimal('2031.91'),
                        Decimal('2040.12')]
    e.value_list = [float(x) for x in e.value_list]
    e.benchmark_list = [float(x) for x in e.benchmark_list]
    e.daily = 19691
    e.update_profit_data({})

    print("1.年化收益率:", e.calculate_annualized_return())
    print("2.累计收益率:", e.calculate_cumulative_return())
    print("3.波动率:", e.calculate_volatility())
    print("4.夏普比率:", e.calculate_sharpe_ratio())
    print("5.日度收益率:", e.calculate_average_daily_return())
    print("6.最大回撤:", e.calculate_max_drawdown())
    print("7.sortino比率:", e.calculate_sortino_ratio())
    print("8.下行风险:", e.calculate_downside_risk())
    print("9.最大回撤期内收益:", e.calculate_max_drawdown_return())
    print("10.资本回报率:", e.calculate_capital_return())
    print("11.信息比率:", e.calculate_information_ratio())
    print("12.负载率:", e.calculate_beta())
    print("13.alpha:", e.calculate_alpha())
    print("14.beta:", e.calculate_beta())
    print("15.R平方:", e.calculate_r_squared())
    print("16.Treynor比率:", e.calculate_treynor_ratio())
    print("17.Calmar比率:", e.calculate_calmar_ratio())
