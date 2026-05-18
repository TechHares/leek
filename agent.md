# Agent 指南：写策略 + 评估

面向 Claude Code / Cursor 这类编码 Agent。用最短路径告诉你：在这个仓库里**写一个新策略**和**验证它**该改哪些文件、调哪些 API。不讲原理，只给步骤。

---

## 1. 项目结构（必读）

```
/Users/shenglin.li/code/leek/
  leek-core/       # 框架（策略基类、回测引擎、指标库）—— 不要在这里加业务策略
  leek-manager/    # 服务层（数据下载脚本、API）
  leek-web/        # 前端

/Users/shenglin.li/code/my-strategy/     # ← 你的策略写这里
  strategy/<your_strategy>.py
  scripts/                                # 评估入口脚本
  models/                                 # 训练好的 ML 模型
```

**所有新策略写到 `/Users/shenglin.li/code/my-strategy/strategy/`**，文件名小写 snake_case。`leek-core` 仅在你需要新指标、新回测特性时才动。

回测/实盘加载策略时用 `mount_dirs=["/Users/shenglin.li/code/my-strategy"]` 注入 `sys.path`，所以 `import` 用 `strategy.your_module.YourStrategy`。

---

## 2. 写一个策略（最小模板）

参考：[`my-strategy/strategy/ma_cross.py`](../my-strategy/strategy/ma_cross.py) 是最干净的趋势模板，148 行涵盖了所有必备模式。

**必须实现 3 个方法**：`on_kline` / `should_open` / `should_close`（继承自 [`CTAStrategy`](leek-core/src/leek_core/strategy/cta.py)）。

```python
# my-strategy/strategy/example.py
from decimal import Decimal
from typing import List, Optional

from leek_core.indicators import MA, RSI, ATR     # 33 个指标在 leek_core.indicators
from leek_core.models import Field, FieldType, KLine, PositionSide
from leek_core.strategy import CTAStrategy


class ExampleStrategy(CTAStrategy):
    display_name: str = "示例策略"
    open_just_no_pos: bool = True   # 同方向已有仓位时不重复开

    # 框架 UI 用这个生成参数表单；写新策略 init_params 必填
    init_params: List[Field] = [
        Field(name="ma_period", label="均线周期", type=FieldType.INT, default=20),
        Field(name="tp_pct", label="止盈(%)", type=FieldType.FLOAT, default=2.0),
        Field(name="sl_pct", label="止损(%)", type=FieldType.FLOAT, default=1.0),
    ]

    def __init__(self, ma_period=20, tp_pct=2.0, sl_pct=1.0):
        super().__init__()
        self.tp_pct = Decimal(str(tp_pct)) / 100
        self.sl_pct = Decimal(str(sl_pct)) / 100
        self.ma = MA(ma_period)         # 指标实例
        self._ma_val = None
        self.k: Optional[KLine] = None
        self.entry_price: Optional[Decimal] = None

    def on_kline(self, kline: KLine):
        """每根 K 线都调用（含未完成的）。先在这里更新所有指标和状态。"""
        self.k = kline
        self._ma_val = self.ma.update(kline)
        if not kline.is_finished:
            return                       # 未完成的 K 线不要做信号判断
        # 此处可以累加 bars_since_close 等冷却变量

    def should_open(self) -> Optional[PositionSide]:
        """返回 PositionSide.LONG / SHORT 即开仓；None 表示不开。"""
        if self._ma_val is None or self.entry_price is not None:
            return None
        if not self.k.is_finished:
            return None
        if self.k.close > self._ma_val:
            self.entry_price = self.k.close
            return PositionSide.LONG
        return None

    def should_close(self, position_side: PositionSide) -> bool:
        """返回 True 平仓；可用 entry_price 算 PnL%。"""
        if self.entry_price is None or not self.k.is_finished:
            return False
        if position_side == PositionSide.LONG:
            pnl = (self.k.close - self.entry_price) / self.entry_price
        else:
            pnl = (self.entry_price - self.k.close) / self.entry_price
        if pnl >= self.tp_pct or pnl <= -self.sl_pct:
            self.entry_price = None
            return True
        return False
```

**几个非显然的约定**（不遵守会出 bug）：

- `entry_price` **必须在 `should_close` 返回 True 时清空**，否则下一根 K 线还会触发 close。
- 未完成的 K 线（`kline.is_finished == False`）只更新指标，**不要发信号**——否则同一根 K 线会触发多次开/平仓。
- 指标 `MA / RSI / ATR / DMI / BOLL / ...` 全部走流式更新：`indicator.update(kline)` 返回当前值（warmup 期返回 `None`）。
- `should_open` 也可以返回 [`StrategyCommand`](leek-core/src/leek_core/strategy/base.py)（不是单纯 `PositionSide`），用于自定义仓位比例、限价单、metadata 标签等高级用法。直接返回 `PositionSide.LONG/SHORT` 就是全仓市价开。

**指标库快速索引**（[`leek-core/src/leek_core/indicators`](leek-core/src/leek_core/indicators)）：

| 类别 | 可用指标 |
|---|---|
| 均线 | `MA`, `EMA`, `WMA`, `HMA`, `KAMA`, `FRAMA`, `LLT` |
| 趋势 | `MACD`, `DMI`, `ADX`, `SAR`, `Donchian`, `Keltner`, `IchimokuCloud` |
| 震荡 | `RSI`, `StochRSI`, `KDJ`, `CCI`, `WR`, `BollBand` |
| 波动 | `ATR`, `TR`, 标准差 |
| 形态 | `ChanKManager`/`ChanBI`/`ChanSegment`（缠论）、影线、TD 序列 |
| 高阶 | `Hurst`, `Lyapunov`, `Reflex`, `TrendFlex`, `RSRS` |

不知道用哪个先用 `MA + RSI + ATR` 起步。

---

## 3. 评估策略（你的核心工作流）

**唯一推荐入口**：[`StrategyEvaluator`](leek-core/src/leek_core/backtest/strategy_evaluation.py)。单策略 / 多策略对比同一个 API，输出 `to_agent_summary()` 你自己 parse 后决定下一步。

### 3.1 单策略快速验证（写完一个策略后立刻调）

```python
from leek_core.backtest import StrategyEvaluator

result = StrategyEvaluator.evaluate(
    strategy=("strategy.example.ExampleStrategy", {"ma_period": 20, "tp_pct": 2.0}),
    symbol="BTC_USDT",
    timeframe="3m",
    start_time="2024-06-01",
    end_time="2025-05-01",
    datasource_class="leek_core.data.ClickHouseKlineDataSource",   # 视你的数据源调整
    datasource_config={"market": "gate"},
    mount_dirs=["/Users/shenglin.li/code/my-strategy"],
)

summary = result.to_agent_summary()
# 用 json.dumps(summary, indent=2, ensure_ascii=False) 打印观察
```

### 3.2 多策略横向对比（决定哪个值得保留）

```python
result = StrategyEvaluator.evaluate(
    strategies=[
        ("strategy.example.ExampleStrategy", {"ma_period": 20}),
        ("strategy.ma_cross.MACrossStrategy", {}),
        ("strategy.bb_regression.BBRegression", {}),
    ],
    symbol="BTC_USDT", timeframe="3m",
    start_time="2024-06-01", end_time="2025-05-01",
    datasource_class="...", datasource_config={...},
    mount_dirs=["/Users/shenglin.li/code/my-strategy"],
    max_workers=4,        # 多策略并行
)
```

### 3.3 读 `to_agent_summary()` 的关键字段

**单策略输出**：

```python
{
  "mode": "single",
  "strategy_id": "00_ExampleStrategy",
  "metrics": {                       # 15 个核心指标
    "sharpe_ratio": 1.2,
    "calmar_ratio": 0.8,
    "total_return": 0.15,
    "max_drawdown": -0.08,
    "win_rate": 0.45,
    "profit_factor": 1.8,
    "t_pvalue": 0.03,                # ← 关键：显著性
    "bootstrap_sharpe_ci": [0.6, 1.8],
    ...
  },
  "evaluation": {                    # 框架已经做的几个 boolean 判断（参考用）
    "is_profitable": true,
    "is_statistically_significant": true,
    "drawdown_acceptable": true,
    "has_enough_trades": true,
    "concerns": [...]                # 框架识别的可疑点
  },
  "regime_breakdown": {              # ← 关键：按市场状态切片
    "trending": {"sharpe": 2.1, "max_drawdown": -0.05, "total_return": 0.18, "n_periods": 12000, "time_share": 0.35},
    "ranging":  {"sharpe": -0.3, "max_drawdown": -0.12, "total_return": -0.03, "n_periods": 22000, "time_share": 0.65},
  }
}
```

**多策略输出**额外有：

```python
{
  "mode": "multi",
  "strategy_count": 3,
  "strategies": { sid: <单策略 summary>, ... },
  "ranking_by_sharpe": [...],        # 按夏普排序
  "correlation_matrix": [[1.0, 0.3, -0.2], ...],   # 策略收益相关性
  "strategy_ids": [...],             # 对应矩阵行/列顺序
}
```

### 3.4 你应该如何读这些指标判断"行不行"

**框架不替你下结论**，但下面是合理的判断标准，按这个走：

1. **`metrics.total_trades < 30`** → 样本不足，再长的回测都是噪声。换更长时间或更短周期重测。
2. **`metrics.t_pvalue >= 0.05`** → 收益跟随机区分度不够，慎用。
3. **`metrics.max_drawdown < -0.30`** → 回撤过大，先看清是单次黑天鹅还是常态，决定加止损还是放弃。
4. **`regime_breakdown.trending.sharpe` 和 `ranging.sharpe` 一正一负** → 策略只在特定 regime 有效。**不是问题**——加一个 regime 过滤器（比如 ADX > 25 才开仓）通常能挽救它。
5. **多策略 `correlation_matrix` 普遍 > 0.7** → 这些策略本质同一逻辑，组合没意义，留夏普最高的那个就行。
6. **多策略最有价值的发现** = 找两个**夏普都 > 0** 且**相关系数 < 0.3** 的策略，组合后整体夏普通常显著提升。

### 3.5 标准工作流（写完一个策略后照这个跑）

1. 单策略 evaluate → 看 `metrics.sharpe_ratio` + `t_pvalue` + `total_trades`：
   - sharpe < 0 或 t_pvalue > 0.1 → 大概率没救，**先看 `regime_breakdown`** 再决定改还是放弃
2. 看 `regime_breakdown`：
   - 某 regime 夏普显著 > 0、另一边显著 < 0 → 加 regime 过滤器后重测
   - 两 regime 都不好 → 信号本身有问题，回去改 `should_open` 逻辑
3. 改完再单策略 evaluate；满意后把它**加入多策略对比集**跑 multi
4. 看 `correlation_matrix` 决定它跟现有策略是替补还是互补

---

## 4. 常见陷阱（写策略时别踩）

- ❌ 在 `__init__` 里读外部文件、调网络。策略实例会被序列化跨进程，会失败。如必须，懒加载到 `on_kline` 第一次调用时。
- ❌ 用 `time.sleep` / 阻塞 IO。事件驱动框架，会拖垮回测速度。
- ❌ 直接用 `print` 调试。用 `logging.getLogger(__name__).info(...)`，回测/实盘的 log handler 是统一管理的。
- ❌ 在 `should_open` 里 mutate 大量状态。状态更新都放 `on_kline`，`should_open` / `should_close` 只读 + 返回决策。
- ❌ 跨时间框架的 K 线在同一个策略里混着用。需要多时间框架的参考 [`grid/`](../my-strategy/strategy/grid) 模块化做法（htf/ltf/mtf 分文件）。
- ❌ Decimal vs float 混用。价格全用 `Decimal`，指标输出是 float，比较时显式转一次。
- ❌ 假设 K 线没缺口。极端行情下会缺，逻辑要能容忍 `pre_kline` 不连续。
- ❌ 测出来 sharpe = 5 兴奋了。先看 `total_trades`、`t_pvalue` 和 `bootstrap_sharpe_ci` —— 多半是过拟合或样本太少。

---

## 5. 数据源 / 历史数据

数据存在 ClickHouse `klines` 表，下载脚本在 [`leek-manager/app/script/`](leek-manager/app/script)：

```bash
# Gate.io（自动分流：archive 旧数据 + API 近期，已处理 10000 根硬限制）
python gate_data_download.py --start=2024-01-01 --end=2025-05-17 \
    --symbols=BTC_USDT,ETH_USDT,...

# OKX
python okx_data_download.py --start=2024-01-01 --end=2025-05-17 \
    --symbols=BTC-USDT-SWAP,ETH-USDT-SWAP,...

# 清理数据库只保留白名单
python cleanup_klines.py            # dry-run
python cleanup_klines.py --execute  # 真删，有二次确认
```

数据库当前保留的 9 个币种（gate + okx 各 9）：BTC / ETH / BNB / XAU(T) / CRV / DOGE / XRP / SOL / PUMP。

---

## 6. 当你被卡住时的捷径

| 问题 | 看哪 |
|---|---|
| 怎么写最简单的趋势策略 | [`my-strategy/strategy/ma_cross.py`](../my-strategy/strategy/ma_cross.py)（148 行，全模式） |
| 怎么写均值回归 | [`my-strategy/strategy/bb_regression.py`](../my-strategy/strategy/bb_regression.py) |
| 怎么写网格（多时间框架） | [`my-strategy/strategy/grid/`](../my-strategy/strategy/grid)（htf/ltf/mtf + risk + trade 模块化） |
| 怎么用 ML | [`my-strategy/strategy/xgboost_m3.py`](../my-strategy/strategy/xgboost_m3.py) + [`scripts/train_xgboost_m3.py`](../my-strategy/scripts/train_xgboost_m3.py) |
| 缠论 | [`my-strategy/strategy/chan.py`](../my-strategy/strategy/chan.py) / [`chan2.py`](../my-strategy/strategy/chan2.py) |
| StrategyCommand 高级用法（限价/部分仓位/metadata） | [`leek-core/src/leek_core/strategy/base.py`](leek-core/src/leek_core/strategy/base.py) line 22-67 |
| 多时间框架数据接入 | [`leek-core/docs/05-dataflow.md`](leek-core/docs/05-dataflow.md) |
| 框架架构 | [`leek-core/docs/20-engine.md`](leek-core/docs/20-engine.md) |

---

## 7. 一个完整的循环（写 → 评估 → 改 → 再评估）

```python
# 1. 写策略 → my-strategy/strategy/my_new.py（按 §2 模板）

# 2. 写评估脚本 → my-strategy/scripts/eval_my_new.py
from leek_core.backtest import StrategyEvaluator
import json

result = StrategyEvaluator.evaluate(
    strategy=("strategy.my_new.MyNewStrategy", {"period": 20}),
    symbol="BTC_USDT", timeframe="3m",
    start_time="2024-06-01", end_time="2025-05-01",
    datasource_class="...", datasource_config={...},
    mount_dirs=["/Users/shenglin.li/code/my-strategy"],
)
print(json.dumps(result.to_agent_summary(), indent=2, ensure_ascii=False))

# 3. 运行
#    python my-strategy/scripts/eval_my_new.py
# 4. 按 §3.4 / §3.5 读 summary 决定下一步
```

**不要写一个策略就发版**——单策略评估通过只是必要条件，最终要看它在**多策略对比 + 不同 symbol + 多时间段**下的稳健性。
