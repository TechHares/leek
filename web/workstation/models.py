import datetime

import psutil
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from multiselectfield import MultiSelectField

# Create your models here.
from leek.common import logger, config
from clickhouse_backend import models as ck_models

from leek.data.data import get_all_data_cls_list
from leek.strategy import get_all_strategies_cls_list
from leek.t import MA_TYPE
from leek.trade.trade import get_all_trader_cls_list
from web.workstation.config import update_config
from web.workstation.worker import WorkerWorkflow


class TradeConfig(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    name = models.CharField(u'名称', max_length=200, unique=True)

    trader_cls = models.CharField(u'执行器类型', null=False, max_length=200, choices=get_all_trader_cls_list())

    # ====================================回测=================================================

    slippage = models.DecimalField(u'滑点幅度', max_digits=8, decimal_places=6, default="0")
    FEE_TYPE_CHOICE = ((0, u'无费用'), (1, u'固定费用'), (2, u'成交额固定比例'), (3, u'单位成交固定费用'),)
    fee_type = models.IntegerField(u'费用收取方式', default=0, choices=FEE_TYPE_CHOICE)
    fee = models.DecimalField(u'费率', max_digits=8, decimal_places=6, default="0")
    min_fee = models.DecimalField(u'单笔最低收费', max_digits=8, decimal_places=6, default="0")
    limit_order_execution_rate = models.IntegerField(u'限价单成交率',
                                                     validators=[MinValueValidator(1),
                                                                 MaxValueValidator(100)],
                                                     default=100)
    volume_limit = models.IntegerField(u'成交量小数保留位数',
                                       validators=[MinValueValidator(0), MaxValueValidator(18)],
                                       default=4)
    # =====================================回测================================================

    # =====================================OKX================================================
    api_key = models.CharField(u'API Key', max_length=200, default="", blank=True)
    api_secret_key = models.CharField(u'Secret Key', max_length=200, default="", blank=True)
    passphrase = models.CharField(u'密码', max_length=200, default="", blank=True)
    leverage = models.IntegerField(u'默认杠杆倍数', default="3", blank=True)

    FLAG_CHOICE = (
        ("1", u"模拟盘"),
        ("0", u'实盘'),
        ("2", u"实盘(AWS)"),
    )
    work_flag = models.CharField(u'盘口', max_length=2, choices=FLAG_CHOICE, default="0")

    #                  , order_type="limit", trade_ins_type=3
    TD_MODE_CHOICE = (
        ("isolated", u'逐仓'),
        ("cross", u"全仓"),
        ("cash", u'非保证金'),
        ("spot_isolated", u'现货带单'),
    )
    td_mode = models.CharField(u'默认交易模式', default="isolated", choices=TD_MODE_CHOICE, max_length=20)
    ccy = models.CharField(u'全仓默认保证金币种(不做全仓可不填)', default=None, null=True, blank=True, max_length=20)
    ORDER_TYPE_CHOICE = (
        ("limit", u'限价'),
        ("market", u"市价"),
    )
    order_type = models.CharField(u'默认下单类型', default="market", choices=ORDER_TYPE_CHOICE, max_length=20)
    slippage_level = models.IntegerField(u'现货/杠杆市价单滑点幅度(1-400档， 设置0直接下市价单)',
                                                     validators=[MinValueValidator(0),
                                                                 MaxValueValidator(400)],
                                                     default=0)
    TRADE_INS_TYPE_CHOICE = ((1, u'现货'), (2, u'杠杆'), (3, u'合约'), (4, u'期货'), (5, u'期权'))
    trade_ins_type = models.IntegerField(u'默认交易产品类型', default=3, choices=TRADE_INS_TYPE_CHOICE)
    # =====================================OKX================================================

    created_time = models.DateTimeField(u'创建时间', auto_now_add=True)

    class Meta:
        verbose_name = "交易执行器"
        verbose_name_plural = "交易执行器"

    def __str__(self):
        return self.name

    def to_dict(self):
        return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])


class DataSourceConfig(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    name = models.CharField(u'名称', max_length=200, unique=True)

    data_cls = models.CharField(u'数据源', null=False, max_length=200, choices=get_all_data_cls_list())

    wsurl = models.CharField(u'WebSocket 地址', max_length=200, default="", blank=True)
    # =====================================OKX================================================
    CHANNEL_CHOICE = (
        ("1s", u"秒K"),
        ("1m", u"分钟K"),
        ("3m", u"3分钟K"),
        ("5m", u"5分钟K"),
        ("15m", u"15分钟K"),
        ("30m", u"30分钟K"),
        ("1H", u"小时K"),
        ("4H", u"4小时K"),
        ("6H", u"6小时K"),
        ("8H", u"8小时K"),
        ("12H", u"12小时K"),
        ("1D", u"日K"),
    )
    channels = MultiSelectField(u'K线选择', max_length=20, default="", choices=CHANNEL_CHOICE, min_choices=1, blank=True)
    symbols = models.TextField(u'InstId(多个逗号隔开)', default="", blank=True)

    interval = models.IntegerField(u'行情刷新周期(秒)', default="300")
    INST_TYPE_CHOICE = (
        ("SPOT", u"币币"),
        ("MARGIN", u'币币杠杆'),
        ("SWAP", u'永续合约'),
        ("FUTURES", u'交割合约'),
        ("OPTION", u'期权'),
    )
    inst_type = models.CharField(u'交易产品', default="SWAP", choices=INST_TYPE_CHOICE, max_length=20)
    FLAG_CHOICE = (
        ("1", u"模拟盘"),
        ("0", u'实盘'),
        ("2", u"实盘(AWS)"),
    )
    work_flag = models.CharField(u'盘口', max_length=2, choices=FLAG_CHOICE, default="0")
    # =====================================OKX================================================

    created_time = models.DateTimeField(u'创建时间', auto_now_add=True)

    class Meta:
        verbose_name = "数据源"
        verbose_name_plural = "数据源"

    def __str__(self):
        return self.name

    def to_dict(self):
        return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])


def time_now():
    return datetime.datetime.now() + datetime.timedelta(days=30)


class StrategyConfig(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    name = models.CharField(u'策略名称', max_length=200, unique=True)
    total_amount = models.DecimalField(u'投入总资产', max_digits=36, decimal_places=12, default="1000")

    # 加载策略列表
    strategy_cls = models.CharField(u'策略', null=False, max_length=200,
                                    choices=get_all_strategies_cls_list(),
                                    default="")
    # =====================================单向单标的网格================================================
    symbol = models.CharField(u'标的物', max_length=200, default="", blank=True)
    min_price = models.DecimalField(u'网格下界', max_digits=36, decimal_places=18, default="0")
    max_price = models.DecimalField(u'网格上界', max_digits=36, decimal_places=18, default="0")
    grid = models.IntegerField(u'网格个数', default="10")
    risk_rate = models.DecimalField(u'风控系数', max_digits=36, decimal_places=6, default="0.1")
    force_risk_rate = models.DecimalField(u'强制风控系数', max_digits=36, decimal_places=6, default="0.2")
    bias_risk_rate = models.DecimalField(u'乖离率反转比例', max_digits=36, decimal_places=6, default="0.2")
    position_split = models.CharField(u'仓位划分', max_length=500, default="1,2,3")
    start_condition = models.CharField(u'开始条件', max_length=500, default="", blank=True)
    stop_condition = models.CharField(u'停止条件', max_length=500, default="", blank=True)
    DIRECTION_CHOICE = (
        (1, u"多"),
        (2, u"空"),
    )
    side = models.IntegerField(u'方向', default=1, choices=DIRECTION_CHOICE)
    rolling_over = models.IntegerField(u'滚动操作', default=0, choices=((1, u"是"), (2, u"否")))
    # =====================================单向单标的网格================================================
    # =====================================均值回归================================================
    symbols = models.CharField(u'标的物(多个「,」分割)', max_length=1000, default="", blank=True)
    direction = models.IntegerField(u'方向', default=4, choices=(
        (1, u"多"),
        (2, u"空"),
        (4, u"多|空"),
    ))
    MEAN_TYPE_CHOICE = [(k, MA_TYPE[k]) for k in MA_TYPE]
    mean_type = models.CharField(u'均值计算方式', max_length=10, default="SMA", blank=True,
                                 choices=MEAN_TYPE_CHOICE)
    window = models.IntegerField(u'均线计算周期', default="10")
    threshold = models.DecimalField(u'阈值', max_digits=36, decimal_places=6, default="0.02")
    take_profit_rate = models.DecimalField(u'止盈比例', max_digits=36, decimal_places=6, default=0.2)
    fallback_percentage = models.DecimalField(u'回落止盈比例', max_digits=36, decimal_places=6,
                                              default=0.05)
    just_finish_k = models.BooleanField(u'仅使用已完成K线数据', default=True)
    max_single_position = models.DecimalField(u'单个标的最大仓位占比', max_digits=36, decimal_places=6,
                                              default=0.2)
    stop_loss_rate = models.DecimalField(u'止损比例', max_digits=36, decimal_places=6, default=0.005)
    num_std_dev = models.DecimalField(u'林带上线轨标准差倍数', max_digits=4, decimal_places=2, default="2.0")
    # =====================================均值回归================================================
    atr_coefficient = models.DecimalField(u'ATR动态止损系数', max_digits=36, decimal_places=6, default=1)
    # =====================================均线================================================
    fast_period = models.IntegerField(u'快线计算周期', default="5")
    slow_period = models.IntegerField(u'慢线计算周期', default="20")
    long_period = models.IntegerField(u'趋势线计算周期', default="60")
    k_merge_period = models.IntegerField(u'K线合并数量', default="0")
    smoothing_period = models.IntegerField(u'平滑周期', default="9")
    factory = models.IntegerField(u'扩展系数', default="2")
    period = models.IntegerField(u'RSI平滑周期', default="10")
    k_smoothing_factor = models.IntegerField(u'StochK平滑周期', default="10")
    d_smoothing_factor = models.IntegerField(u'StochD平滑周期', default="10")
    k_num = models.IntegerField(u'MACD周期聚合', default="10")
    min_histogram_num = models.IntegerField(u'最小MACD能量柱数', default="10")
    position_num = models.IntegerField(u'分仓', default="2")
    open_change_rate = models.DecimalField(u'加仓变化率限制', max_digits=8, decimal_places=6, default="0.01")
    close_change_rate = models.DecimalField(u'平仓变化率限制', max_digits=8, decimal_places=6, default="0.01")
    close_position_when_direction_change = models.BooleanField(u'趋势反转时优先平仓', default=True)
    PRICE_TYPE_CHOICE = (
        (1, u"收盘价"),
        (2, u"最高价"),
        (3, u"最低价"),
        (4, u"开盘价"),
        (5, u"平均价"),
        (6, u"avg(high+low)"),
        (7, u"avg(high+low+close)"),
        (8, u"avg(open+high+low+close)"),
    )
    price_type = models.IntegerField(u'Basic取值', default=1, choices=PRICE_TYPE_CHOICE)
    open_channel = models.IntegerField(u'唐奇安通道周期(开仓)', default="20")
    close_channel = models.IntegerField(u'唐奇安通道周期(平仓)', default="10")
    true_range_window = models.IntegerField(u'波动率平滑周期', default="20")
    expected_value = models.DecimalField(u'期望账户净值波动', max_digits=36, decimal_places=6, default=0.01)
    add_position_rate = models.DecimalField(u'加仓阈值', max_digits=36, decimal_places=6, default=0.5)
    close_position_rate = models.DecimalField(u'止损阈值', max_digits=36, decimal_places=6, default=2)
    half_needle = models.BooleanField(u'唐奇安通道影线折半计算', default=True)
    open_vhf_threshold = models.DecimalField(u'vhf开仓阈值(开仓)', max_digits=36, decimal_places=6, default=0.5)
    close_vhf_threshold = models.DecimalField(u'vhf平仓阈值(平仓)', max_digits=36, decimal_places=6, default=0.0)
    take_profit_period = models.IntegerField(u'vmma计算周期(平仓)', default="10")
    over_buy = models.IntegerField(u'超买阈值', default="80", validators=[MinValueValidator(-1000), MaxValueValidator(1000)])
    over_sell = models.IntegerField(u'超卖阈值', default="20", validators=[MinValueValidator(-1000), MaxValueValidator(1000)])
    peak_over_buy = models.IntegerField(u'极限超买阈值', default="90", validators=[MinValueValidator(0), MaxValueValidator(100)])
    peak_over_sell = models.IntegerField(u'极限超卖阈值', default="10",validators=[MinValueValidator(0), MaxValueValidator(100)])
    TRADE_TYPE_CHOICE = (
        (0, u"顺势|反转"),
        (1, u"顺势"),
        (2, u"反转"),
    )
    trade_type = models.IntegerField(u'参与交易类型', default=0, choices=TRADE_TYPE_CHOICE)
    win_loss_target = models.DecimalField(u'反转交易预期盈亏比', max_digits=36, decimal_places=6, default=2.0)
    data_source = models.ForeignKey(DataSourceConfig, on_delete=models.PROTECT, verbose_name=u'数据源')
    trade = models.ForeignKey(TradeConfig, on_delete=models.PROTECT, verbose_name=u'交易器')
    limit_threshold = models.IntegerField(u'完全平仓阈值(连续平仓之后先清仓)', default=5, null=True)
    STATUS_CHOICE = (
        (1, u"停止"),
        (2, u"运行"),
        (3, u"运行中"),
    )
    status = models.IntegerField(u'状态', default=1, choices=STATUS_CHOICE)
    process_id = models.IntegerField(u'进程ID', default=0, null=True)
    end_time = models.DateTimeField(u'结束时间', default=time_now, null=True)
    run_data = models.JSONField(u'运行数据', default=None, blank=True, null=True)
    created_time = models.DateTimeField(u'创建时间', auto_now_add=True)

    class Meta:
        verbose_name = "策略"
        verbose_name_plural = "策略管理"

    def __str__(self):
        return self.name

    def to_dict(self):
        return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])

    def save(
            self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.id and self.id > 0:
            st = StrategyConfig.objects.get(id=self.id)
            if st.process_id and st.process_id > 0 and self.status != 3:
                WorkerWorkflow.send_command("shutdown", self.id)
                self.process_id = 0
        if self.status == 1 or self.run_data is None:
            self.run_data = {}
        super().save(force_insert, force_update, using, update_fields)

    def just_save(self):
        super().save()


if config.DATA_DB.type == 'CLICKHOUSE':
    class Kline(ck_models.ClickhouseModel):
        id = models.BigAutoField(u'id', primary_key=True)
        interval = ck_models.StringField(u'周期', max_length=5, default="", null=False)
        timestamp = ck_models.UInt64Field(u'时间戳', default=0, null=False)
        symbol = ck_models.StringField(u'标的', max_length=20, default="", null=False)
        open = ck_models.DecimalField(u'开盘价', max_digits=18, decimal_places=8, default=0, null=False)
        high = ck_models.DecimalField(u'最高价', max_digits=18, decimal_places=8, default=0, null=False)
        low = ck_models.DecimalField(u'最低价', max_digits=18, decimal_places=8, default=0, null=False)
        close = ck_models.DecimalField(u'收盘价', max_digits=18, decimal_places=8, default=0, null=False)
        volume = ck_models.DecimalField(u'成交量', max_digits=18, decimal_places=4, default=0, null=False)
        amount = ck_models.DecimalField(u'成交额', max_digits=18, decimal_places=2, default=0, null=False)

        class Meta:
            db_tablespace = "data"
            verbose_name = "回测K线数据"
            verbose_name_plural = "回测K线数据"
            unique_together = ('interval', "timestamp", "symbol")
            ordering = ["-timestamp"]
            engine = ck_models.ReplacingMergeTree(
                primary_key=("interval", "timestamp", "symbol"),
                order_by=("interval", "timestamp", "symbol"),
                partition_by="interval",
                index_granularity=4096,
                index_granularity_bytes=1 << 20,
                enable_mixed_granularity_parts=1,
            )

        def __str__(self):
            return "%s-%s-%s" % (self.interval, self.symbol, self.symbol)

        def to_dict(self):
            return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])

else:
    class Kline(models.Model):
        id = models.BigAutoField(u'id', primary_key=True)
        interval = models.CharField(u'周期', max_length=5, default="", null=False)
        timestamp = models.BigIntegerField(u'时间戳', default=0, null=False)
        symbol = models.CharField(u'标的', max_length=20, default="", null=False)
        open = models.DecimalField(u'开盘价', max_digits=18, decimal_places=8, default=0, null=False)
        high = models.DecimalField(u'最高价', max_digits=18, decimal_places=8, default=0, null=False)
        low = models.DecimalField(u'最低价', max_digits=18, decimal_places=8, default=0, null=False)
        close = models.DecimalField(u'收盘价', max_digits=18, decimal_places=8, default=0, null=False)
        volume = models.DecimalField(u'成交量', max_digits=18, decimal_places=4, default=0, null=False)
        amount = models.DecimalField(u'成交额', max_digits=18, decimal_places=2, default=0, null=False)

        class Meta:
            verbose_name = "回测K线数据"
            verbose_name_plural = "回测K线数据"
            unique_together = ('interval', "timestamp", "symbol")
            ordering = ["-timestamp"]
            db_tablespace = "data"
            indexes = [
                models.Index(fields=['symbol']),
            ]

        def __str__(self):
            return "%s" % self.id

        def to_dict(self):
            return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])


class TradeLog(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    order_id = models.CharField(u'订单ID', max_length=200, default="", null=False)
    strategy_id = models.BigIntegerField(u'策略ID', default=0, null=False)
    type = models.IntegerField(u'类型', default=0, null=False)
    symbol = models.CharField(u'标的', max_length=20, default="", null=False)
    price = models.DecimalField(u'价格', max_digits=18, decimal_places=8, default=0, null=False)
    amount = models.DecimalField(u'数量', max_digits=18, decimal_places=8, default=0, null=False)
    sz = models.DecimalField(u'换算数量', max_digits=18, decimal_places=8, default=0, null=False)
    side = models.IntegerField(u'方向', default=0, null=False, choices=StrategyConfig.DIRECTION_CHOICE)
    timestamp = models.DateTimeField(u'时间戳', default=None, null=False)
    transaction_volume = models.DecimalField(u'成交数量', max_digits=18, decimal_places=8, default=0, null=False)
    transaction_amount = models.DecimalField(u'成交金额', max_digits=18, decimal_places=8, default=0, null=False)
    transaction_price = models.DecimalField(u'价格', max_digits=18, decimal_places=8, default=0, null=False)
    fee = models.DecimalField(u'费用', max_digits=18, decimal_places=8, default=0, null=False)
    avg_price = models.DecimalField(u'平均持仓价格', max_digits=18, decimal_places=8, default=0, null=False)
    quantity = models.DecimalField(u'持仓数量', max_digits=18, decimal_places=8, default=0, null=False)

    class Meta:
        verbose_name = "交易记录"
        verbose_name_plural = "交易记录"
        db_tablespace = "data"

    def __str__(self):
        return self.order_id


class ProfitLog(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    strategy_id = models.BigIntegerField(u'策略ID', default=0, null=False)
    timestamp = models.BigIntegerField(u'时间戳', default=None, null=False)
    value = models.DecimalField(u'价值', max_digits=18, decimal_places=8, default=0, null=False)
    profit = models.DecimalField(u'累计利润', max_digits=18, decimal_places=8, default=0, null=False)
    fee = models.DecimalField(u'费用', max_digits=18, decimal_places=8, default=0, null=False)

    class Meta:
        verbose_name = "价值统计"
        verbose_name_plural = "价值统计"
        db_tablespace = "data"

    def __str__(self):
        return "%s-%s" % (self.strategy_id, self.timestamp)


class RuntimeConfig(models.Model):
    id = models.BigAutoField(u'id', primary_key=True)
    LOG_LEVEL_CHOICE = (
        ("CRITICAL", 'CRITICAL'),
        ("ERROR", 'ERROR'),
        ("WARNING", 'WARNING'),
        ("INFO", 'INFO'),
        ("DEBUG", 'DEBUG'),
        ("NOTSET", 'NOTSET'),
    )
    log_level = models.CharField(u'日志等级', max_length=20, default="INFO", blank=False, choices=LOG_LEVEL_CHOICE)
    data_dir = models.CharField(u'数据存储目录', max_length=200, default="data", blank=False)
    download_dir = models.CharField(u'下载数据目录', max_length=200, default="download", blank=False)
    proxy = models.CharField(u'网络代理(例: http://127.0.0.1:6789)', max_length=200, default=None, blank=True, null=True)

    order_alert = models.BooleanField(u'开单提醒', default=False)
    min_rate = models.DecimalField(u'最小下单仓位', validators=[MinValueValidator(0), MaxValueValidator(1)],
                                   max_digits=8, decimal_places=4, default="0.005")
    rolling_position = models.BooleanField(u'滚仓操作', default=True)


    emulation = models.BooleanField(u'回测数据仿真(开启后会使用小级别数据穿插在K线中)', default=False)
    emulation_interval = models.CharField(u'仿真填充K线', max_length=5, default="5m", choices=DataSourceConfig.CHANNEL_CHOICE)
    target_interval = models.CharField(u'需仿真K线', max_length=5, default="30m", choices=DataSourceConfig.CHANNEL_CHOICE)

    filter_release_strategy = models.BooleanField(u'只显示已发布策略(经过大量实盘的测试，PS： !=赚钱)', default=False)
    clear_run_data_on_error = models.BooleanField(u'运行异常时清空策略run_data', default=True)
    stop_on_error = models.BooleanField(u'运行异常时停止策略', default=False)
    allow_share_trading_account = models.BooleanField(u'允许策略间共享交易账户(开启后多个策略可使用同一个账户)', default=False)

    ALERT_TYPE_CHOICE = (
        ("console", u'控制台输出'),
        ("dingding", u'钉钉'),
    )
    alert_type = models.CharField(u'通知方式', default="console", max_length=30, blank=False, choices=ALERT_TYPE_CHOICE)
    alert_token = models.CharField(u'通知token', max_length=500, default=None, blank=True,
                                      null=True)

    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        super().save(force_insert, force_update, using, update_fields)
        update_config(self)
        WorkerWorkflow.send_command("config_update")

    class Meta:
        verbose_name = "设置"
        verbose_name_plural = "设置"
