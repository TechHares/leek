### LLT(Low-lag Trendline)

低延迟趋势线，通过信号处理理论中的一些滤波方法，克服了MA指标的进行趋势跟踪时，容易出现「跟不紧」甚至「跟不上」的缺点，可以实现低延迟趋势跟踪

涉及Z变换、傅里叶变换和拉普拉斯变换， 最后定义为：

$$
{LLT_t} = {(a-\frac{a^2}{4}) * {price_t} + \frac{a^2}{2}*{price_{t-1}} - (a-\frac{3{a^2}}{4})*{price_{t-2}}} + {2(1-a){LLT_{t-1}} - {(1-a)^2{LLT_{t-2}}}}
$$

推导过程见[参考资料](https://bigquant.com/wiki/static/upload/5f/5fe20094-b60a-442f-a8e3-fda8a6175cbb.pdf)
