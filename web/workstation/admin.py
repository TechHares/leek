import json
from urllib.parse import unquote

import cachetools
from django.contrib import admin
from django.db import connections
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseRedirect
from django.urls import path
from import_export.admin import ImportExportModelAdmin

from leek.common.utils import all_constructor_args, get_cls
from leek.data.data import get_all_data_cls_list
from leek.strategy import get_all_strategies_cls_list
from leek.trade.trade import get_all_trader_cls_list
from .models import TradeConfig, DataSourceConfig, StrategyConfig, TradeLog, RuntimeConfig


# Register your models here.


class TradeConfigAdmin(admin.ModelAdmin):
    # 定制哪些字段需要展示
    list_display = ('name', 'trader_cls', 'created_time')

    list_display_links = ('name',)  # 默认
    sortable_by = ('created_time',)  # 排序

    '''分页：每页10条'''
    list_per_page = 10
    search_fields = ['name']
    empty_value_display = ''

    list_filter = ('trader_cls', 'created_time',)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'trader_cls':
            kwargs['choices'] = get_all_trader_cls_list()
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    class Media:
        js = ('js/trade_config.js',)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('update_cls/', self.update_trader_cls),
        ]
        return my_urls + urls

    def update_trader_cls(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
            trader_cls = request.POST.get('trader_cls', None)
            if trader_cls:
                # 根据 trader_cls 返回相应的字段列表
                pre = trader_cls.split('|')
                fixed_fields = ['id', 'name', 'trader_cls', 'created_time']
                args = all_constructor_args(get_cls(pre[0], pre[1]))
                fields = [f.name for f in TradeConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f in args]
                fields_to_hide = [f for f in fields if f not in fields_to_show]
            else:
                fields_to_show = []
                fields_to_hide = []
            response_data = {
                'fields_to_show': fields_to_show,
                'fields_to_hide': fields_to_hide,
            }

            return JsonResponse(response_data)
        else:
            return JsonResponse({'error': 'Invalid request'})


class DataSourceConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'data_cls', 'created_time')
    list_display_links = ('name',)  # 默认
    sortable_by = ('created_time',)  # 排序

    '''分页：每页10条'''
    list_per_page = 10
    search_fields = ['name']
    empty_value_display = ''

    list_filter = ('data_cls', 'created_time',)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'data_cls':
            kwargs['choices'] = get_all_data_cls_list()
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    class Media:
        js = ('js/data_config.js',)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('update_cls/', self.update_trader_cls),
        ]
        return my_urls + urls

    def update_trader_cls(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
            trader_cls = request.POST.get('data_cls', None)
            if trader_cls:
                # 根据 trader_cls 返回相应的字段列表
                pre = trader_cls.split('|')
                fixed_fields = ['id', 'name', 'data_cls', 'created_time']
                args = all_constructor_args(get_cls(pre[0], pre[1]))
                fields = [f.name for f in DataSourceConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f in args]
                fields_to_hide = [f for f in fields if f not in fields_to_show]

            else:
                fields_to_show = []
                fields_to_hide = []
            # if trader_cls:
            #     # 根据 trader_cls 返回相应的字段列表
            #     pre = trader_cls.split('|')[1].lower()
            #     fixed_fields = ['id', 'name', 'data_cls', 'created_time']
            #     fields = [f.name for f in DataSourceConfig._meta.get_fields() if f.name not in fixed_fields]
            #     fields_to_show = [f for f in fields if f.startswith(pre)]
            #     fields_to_hide = [f for f in fields if not f.startswith(pre)]
            # else:
            #     fields_to_show = []
            #     fields_to_hide = []
            response_data = {
                'fields_to_show': fields_to_show,
                'fields_to_hide': fields_to_hide,
            }

            return JsonResponse(response_data)
        else:
            return JsonResponse({'error': 'Invalid request'})


class StrategyConfigAdmin(admin.ModelAdmin):
    change_form_template = "workstation/strategy_form.html"
    list_display = ('name', 'strategy_cls', 'data_source', 'trade', 'total_amount', 'profit', 'fee',
                    'status', 'process_id', 'end_time')
    list_display_links = ('name',)  # 默认
    readonly_fields = ('run_data',)
    sortable_by = ('status desc', 'created_time desc',)  # 排序

    '''分页：每页10条'''
    list_per_page = 10
    search_fields = ['name']
    empty_value_display = ''

    list_filter = ('strategy_cls', 'created_time', 'status',)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'strategy_cls':
            kwargs['choices'] = get_all_strategies_cls_list()

        if db_field.name == 'status':
            kwargs['choices'] = StrategyConfig.STATUS_CHOICE
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    class Media:
        js = ('js/strategy_config.js',)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('update_cls/', self.update_trader_cls),
            path('backtest/', self.backtest),
        ]
        return my_urls + urls

    def backtest(self, request):
        # data = json.loads(request.headers.get("data"))
        # print(data)
        from leek.runner.backtest import BacktestWorkflow
        data = json.loads(unquote(request.GET.get('data'), 'utf-8'))
        w = BacktestWorkflow(data)
        w.start()

        def report_generator():
            while x := w.report():
                yield f'event: {x["type"]}\ndata: {x["data"]}\n\n'

        return StreamingHttpResponse(report_generator(), content_type='text/event-stream')

    def update_trader_cls(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
            trader_cls = request.POST.get('strategy_cls', None)
            if trader_cls:
                # 根据 trader_cls 返回相应的字段列表
                pre = trader_cls.split('|')
                fixed_fields = ['id', 'name', 'strategy_cls', 'total_amount', 'data_source', 'trade', 'status',
                                'end_time', 'created_time', 'run_data']
                args = all_constructor_args(get_cls(pre[0], pre[1]))
                fields = [f.name for f in StrategyConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f in args]
                fields_to_hide = [f for f in fields if f not in fields_to_show]

            else:
                fields_to_show = []
                fields_to_hide = []

            fields_to_hide.append("process_id")
            # fields_to_hide.append("run_data")
            response_data = {
                'fields_to_show': fields_to_show,
                'fields_to_hide': fields_to_hide,
            }

            return JsonResponse(response_data)
        else:
            return JsonResponse({'error': 'Invalid request'})

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update(
            {
                'datasource_channel_choice': DataSourceConfig.CHANNEL_CHOICE,
                'datasource_symbol_choice': self.all_symbol(),
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    @cachetools.cached(cache=cachetools.TTLCache(maxsize=20, ttl=600))
    def all_symbol(self):
        with connections["data"].cursor() as cursor:
            cursor.execute("select distinct symbol from workstation_kline order by symbol")
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def position_value(self, obj):
        if obj.run_data is None:
            return ""
        return obj.run_data.get('position_value', '')

    def profit(self, obj):
        if obj.run_data is None:
            return ""
        return obj.run_data.get('profit', '')

    def fee(self, obj):
        if obj.run_data is None:
            return ""
        return obj.run_data.get('fee', '')

    def available_amount(self, obj):
        if obj.run_data is None:
            return ""
        return obj.run_data.get('available_amount', '')

    position_value.short_description = '当前价值'
    available_amount.short_description = '可用余额'
    profit.short_description = '利润'
    fee.short_description = '总费用'


class TradeLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_id', 'strategy_id', 'side', 'price', 'amount', 'quantity', 'avg_price', 'fee', 'timestamp')
    list_display_links = ('id',)
    sortable_by = ('id desc',)
    list_per_page = 10
    # search_fields = ['order_id', 'strategy_id']
    empty_value_display = ''

    list_filter = ('order_id', 'strategy_id')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class KlineIntervalFilter(admin.SimpleListFilter):
    title = '周期'
    parameter_name = 'interval'

    def lookups(self, request, model_admin):
        return DataSourceConfig.CHANNEL_CHOICE

    def queryset(self, request, queryset):
        if self.value() is None:
            self.used_parameters.setdefault(self.parameter_name, "1m")


class SettingModelAdmin(admin.ModelAdmin):
    show_save_and_continue = False
    fieldsets = [
        ("基础设置", {"fields" : ("log_level", "data_dir", "download_dir", "proxy")}),
        ("交易设置", {"fields" : ("order_alert", "min_rate", "rolling_position")}),
        ("回测设置", {"fields" : ("emulation", "emulation_interval", "target_interval")}),
        ("告警设置", {"fields" : ("alert_type", "alert_token")})
    ]

    def changelist_view(self, request):
        return HttpResponseRedirect("1/change")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if not RuntimeConfig.objects.filter(id=1).exists():
            RuntimeConfig.objects.create(id=1)
        return super().change_view(request, "1", form_url, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
# class KlineAdmin(ImportExportModelAdmin):
#     list_display = ('symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount',)
#     list_display_links = ('symbol',)
#     sortable_by = ('timestamp desc',)
#     list_filter = (KlineIntervalFilter, 'symbol', 'timestamp',)
#     list_per_page = 10


admin.site.register(RuntimeConfig, SettingModelAdmin)
admin.site.register(TradeConfig, TradeConfigAdmin)
admin.site.register(DataSourceConfig, DataSourceConfigAdmin)
admin.site.register(StrategyConfig, StrategyConfigAdmin)
admin.site.register(TradeLog, TradeLogAdmin)
# admin.site.register(Kline, KlineAdmin)
admin.site.site_header = '量 韭 '
admin.site.site_title = ' 量 韭 '
admin.site.index_title = ' 量 韭 '
