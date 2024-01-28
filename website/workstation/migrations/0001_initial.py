# Generated by Django 4.2.8 on 2024-01-28 03:39
import sys

import clickhouse_backend
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields
import workstation.models

from leek.common.config import KLINE_DB_TYPE


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataSourceConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='名称')),
                ('data_cls', models.CharField(choices=[('leek.data.data_okx|OkxKlineDataSource', 'OKX行情')], max_length=200, verbose_name='数据源')),
                ('okxklinedatasource_url', models.CharField(blank=True, default='', max_length=200, verbose_name='WebSocket 地址')),
                ('okxklinedatasource_channels', multiselectfield.db.fields.MultiSelectField(choices=[('1s', '秒K'), ('1m', '分钟K'), ('3m', '3分钟K'), ('5m', '5分钟K'), ('15m', '15分钟K'), ('30m', '30分钟K'), ('1H', '小时K'), ('4H', '4小时K'), ('1D', '日K')], default='', max_length=20, verbose_name='K线选择')),
                ('okxklinedatasource_symbols', models.TextField(default='', verbose_name='InstId(多个逗号隔开)')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '数据源',
                'verbose_name_plural': '数据源',
            },
        ),
        migrations.CreateModel(
            name='ProfitLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                ('strategy_id', models.BigIntegerField(default=0, verbose_name='策略ID')),
                ('timestamp', models.BigIntegerField(default=None, verbose_name='时间戳')),
                ('value', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='价值')),
                ('profit', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='累计利润')),
                ('fee', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='费用')),
            ],
            options={
                'verbose_name': '价值统计',
                'verbose_name_plural': '价值统计',
                'db_tablespace': 'data',
            },
        ),
        migrations.CreateModel(
            name='TradeConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='名称')),
                ('trader_cls', models.CharField(choices=[('leek.trade.trade_backtest|BacktestTrader', '虚拟交易(回测)'), ('leek.trade.trade_okx|OkxTrader', 'OKX交易')], max_length=200, verbose_name='执行器类型')),
                ('backtesttrader_slippage', models.DecimalField(decimal_places=2, default='0', max_digits=8, verbose_name='滑点幅度')),
                ('backtesttrader_fee_type', models.IntegerField(choices=[(0, '无费用'), (1, '固定费用'), (2, '成交额固定比例'), (3, '单位成交固定费用')], default=0, verbose_name='费用收取方式')),
                ('backtesttrader_fee', models.DecimalField(decimal_places=2, default='0', max_digits=8, verbose_name='费率')),
                ('backtesttrader_min_fee', models.DecimalField(decimal_places=2, default='0', max_digits=8, verbose_name='单笔最低收费')),
                ('backtesttrader_limit_order_execution_rate', models.IntegerField(default=100, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)], verbose_name='限价单成交率')),
                ('backtesttrader_volume_limit', models.IntegerField(default=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(18)], verbose_name='成交量小数保留位数')),
                ('okxtrader_api_key', models.CharField(blank=True, default='', max_length=200, verbose_name='API Key')),
                ('okxtrader_api_secret_key', models.CharField(blank=True, default='', max_length=200, verbose_name='Secret Key')),
                ('okxtrader_passphrase', models.CharField(blank=True, default='', max_length=200, verbose_name='密码')),
                ('okxtrader_leverage', models.CharField(blank=True, default='', max_length=200, verbose_name='杠杆倍数')),
                ('okxtrader_domain', models.CharField(blank=True, default='', max_length=200, verbose_name='交易Rest域名')),
                ('okxtrader_ws_domain', models.CharField(blank=True, default='', max_length=200, verbose_name='交易WebSocket域名')),
                ('okxtrader_pub_domain', models.CharField(blank=True, default='', max_length=200, verbose_name='公共数据域名')),
                ('okxtrader_acct_domain', models.CharField(blank=True, default='', max_length=200, verbose_name='账号操作域名')),
                ('okxtrader_flag', models.CharField(choices=[('1', '模拟盘'), ('0', '实盘')], default='0', max_length=2, verbose_name='盘口')),
                ('okxtrader_inst_type', models.CharField(choices=[('SPOT', '币币'), ('MARGIN', '币币杠杆'), ('SWAP', '永续合约'), ('FUTURES', '交割合约'), ('OPTION', '期权')], default='SWAP', max_length=20, verbose_name='交易产品')),
                ('okxtrader_td_mode', models.CharField(choices=[('isolated', '逐仓'), ('cross', '全仓'), ('cash', '非保证金')], default='isolated', max_length=20, verbose_name='交易模式')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '交易执行器',
                'verbose_name_plural': '交易执行器',
            },
        ),
        migrations.CreateModel(
            name='TradeLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                ('order_id', models.CharField(default='', max_length=200, verbose_name='订单ID')),
                ('strategy_id', models.BigIntegerField(default=0, verbose_name='策略ID')),
                ('type', models.IntegerField(default=0, verbose_name='类型')),
                ('symbol', models.CharField(default='', max_length=20, verbose_name='标的')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='价格')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='数量')),
                ('sz', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='换算数量')),
                ('side', models.IntegerField(choices=[(1, '多'), (2, '空')], default=0, verbose_name='方向')),
                ('timestamp', models.DateTimeField(default=None, verbose_name='时间戳')),
                ('transaction_volume', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='成交数量')),
                ('transaction_amount', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='成交金额')),
                ('transaction_price', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='价格')),
                ('fee', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='费用')),
                ('avg_price', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='平均持仓价格')),
                ('quantity', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='持仓数量')),
            ],
            options={
                'verbose_name': '交易记录',
                'verbose_name_plural': '交易记录',
                'db_tablespace': 'data',
            },
        ),
        migrations.CreateModel(
            name='StrategyConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='策略名称')),
                ('total_amount', models.DecimalField(decimal_places=2, default='0', max_digits=36, verbose_name='投入总资产')),
                ('strategy_cls', models.CharField(choices=[('leek.strategy.strategy_grid|SingleGridStrategy', '单向单标的网格'), ('leek.strategy.strategy_mean_reverting|MeanRevertingStrategy', '均值回归')], default='', max_length=200, verbose_name='策略')),
                ('singlegridstrategy_symbol', models.CharField(blank=True, default='', max_length=200, verbose_name='标的物')),
                ('singlegridstrategy_min_price', models.DecimalField(decimal_places=6, default='0', max_digits=36, verbose_name='网格下界')),
                ('singlegridstrategy_max_price', models.DecimalField(decimal_places=6, default='0', max_digits=36, verbose_name='网格上界')),
                ('singlegridstrategy_grid', models.IntegerField(default='10', verbose_name='网格个数')),
                ('singlegridstrategy_risk_rate', models.DecimalField(decimal_places=6, default='0.1', max_digits=36, verbose_name='风控系数')),
                ('singlegridstrategy_direction', models.IntegerField(choices=[(1, '多'), (2, '空')], default=1, verbose_name='方向')),
                ('singlegridstrategy_rolling_over', models.IntegerField(choices=[(1, '是'), (2, '否')], default=0, verbose_name='滚动操作')),
                ('meanrevertingstrategy_symbols', models.CharField(blank=True, default='', max_length=1000, verbose_name='标的物')),
                ('meanrevertingstrategy_direction', models.IntegerField(choices=[(1, '多'), (2, '空'), (4, '多|空')], default=4, verbose_name='方向')),
                ('meanrevertingstrategy_mean_type', models.CharField(blank=True, choices=[('SMA', 'SMA'), ('EMA', 'EMA')], default='SMA', max_length=10, verbose_name='均值计算方式')),
                ('meanrevertingstrategy_lookback_intervals', models.IntegerField(default='10', verbose_name='均线计算周期')),
                ('meanrevertingstrategy_threshold', models.DecimalField(decimal_places=6, default='0.02', max_digits=36, verbose_name='阈值')),
                ('meanrevertingstrategy_take_profit_rate', models.DecimalField(decimal_places=6, default=0.2, max_digits=36, verbose_name='止盈比例')),
                ('meanrevertingstrategy_fallback_percentage', models.DecimalField(decimal_places=6, default=0.05, max_digits=36, verbose_name='回落止盈比例')),
                ('meanrevertingstrategy_max_single_position', models.DecimalField(decimal_places=6, default=0.2, max_digits=36, verbose_name='单个标的最大仓位占比')),
                ('meanrevertingstrategy_stop_loss_rate', models.DecimalField(decimal_places=6, default=0.005, max_digits=36, verbose_name='止损比例')),
                ('status', models.IntegerField(choices=[(1, '停止'), (2, '运行'), (3, '运行中')], default=1, verbose_name='状态')),
                ('process_id', models.IntegerField(default=0, null=True, verbose_name='进程ID')),
                ('end_time', models.DateTimeField(default=workstation.models.time_now, null=True, verbose_name='结束时间')),
                ('run_data', models.JSONField(blank=True, default=None, null=True, verbose_name='运行数据')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('data_source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='workstation.datasourceconfig', verbose_name='数据源')),
                ('trade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='workstation.tradeconfig', verbose_name='交易器')),
            ],
            options={
                'verbose_name': '策略',
                'verbose_name_plural': '策略管理',
            },
        ),
    ]
    if KLINE_DB_TYPE == "CLICKHOUSE":
        operations.append(
            migrations.CreateModel(
                name='Kline',
                fields=[
                    (
                        'id',
                        models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('interval', clickhouse_backend.models.StringField(default='', max_length=5, verbose_name='周期')),
                    ('timestamp', clickhouse_backend.models.UInt64Field(default=0, verbose_name='时间戳')),
                    ('symbol', clickhouse_backend.models.StringField(default='', max_length=20, verbose_name='标的')),
                    ('open', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                    verbose_name='开盘价')),
                    ('high', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                    verbose_name='最高价')),
                    ('low', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                   verbose_name='最低价')),
                    ('close', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                     verbose_name='收盘价')),
                    ('volume', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                      verbose_name='成交量')),
                    ('amount', clickhouse_backend.models.DecimalField(decimal_places=2, default=0, max_digits=36,
                                                                      verbose_name='成交额')),
                ],
                options={
                    'verbose_name': '回测K线数据',
                    'verbose_name_plural': '回测K线数据',
                    'ordering': ['-timestamp'],
                    'db_tablespace': 'data',
                    'engine': clickhouse_backend.models.MergeTree(enable_mixed_granularity_parts=1,
                                                                  index_granularity=4096,
                                                                  index_granularity_bytes=1048576,
                                                                  order_by=('interval', 'timestamp', 'symbol'),
                                                                  partition_by='interval',
                                                                  primary_key=('interval', 'timestamp', 'symbol')),
                    'unique_together': {('timestamp', 'symbol')},
                },
                managers=[
                    ('objects', django.db.models.manager.Manager()),
                    ('_overwrite_base_manager', django.db.models.manager.Manager()),
                ],
            )
        )
    else:
        operations.append(
            migrations.CreateModel(
                name='Kline',
                fields=[
                    ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='id')),
                    ('interval', models.CharField(default='', max_length=5, verbose_name='周期')),
                    ('timestamp', models.BigIntegerField(default=0, verbose_name='时间戳')),
                    ('symbol', models.CharField(default='', max_length=20, verbose_name='标的')),
                    ('open', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='开盘价')),
                    ('high', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='最高价')),
                    ('low', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='最低价')),
                    ('close', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='收盘价')),
                    ('volume', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='成交量')),
                    ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=36, verbose_name='成交额')),
                ],
                options={
                    'verbose_name': '回测K线数据',
                    'verbose_name_plural': '回测K线数据',
                    'ordering': ['-timestamp'],
                    'db_tablespace': 'data',
                    'unique_together': {('interval', 'timestamp', 'symbol')},
                },
            )
        )
    db = [arg.split("=")[1] for arg in sys.argv if arg.startswith("--database")]
    if len(db) > 0 and db[0] == "data":
        operations = [o for o in operations if "db_tablespace" in o.options and
                      o.options["db_tablespace"] == "data"]
    else:
        operations = [o for o in operations if "db_tablespace" not in o.options or
                      o.options["db_tablespace"] == "default"]

