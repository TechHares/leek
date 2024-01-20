import json
from urllib.parse import unquote

from django.contrib import admin
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path
from import_export.admin import ImportExportModelAdmin
from .models import TradeConfig, DataSourceConfig, StrategyConfig, TradeLog, Kline


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
            kwargs['choices'] = TradeConfig.TRADER_TYPE_CHOICE
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
                pre = trader_cls.split('|')[1].lower()
                fixed_fields = ['id', 'name', 'trader_cls', 'created_time']
                fields = [f.name for f in TradeConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f.startswith(pre)]
                fields_to_hide = [f for f in fields if not f.startswith(pre)]
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
            kwargs['choices'] = DataSourceConfig.DATA_SOURCE_TYPE_CHOICE
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
                pre = trader_cls.split('|')[1].lower()
                fixed_fields = ['id', 'name', 'data_cls', 'created_time']
                fields = [f.name for f in DataSourceConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f.startswith(pre)]
                fields_to_hide = [f for f in fields if not f.startswith(pre)]
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


class StrategyConfigAdmin(admin.ModelAdmin):
    change_form_template = "workstation/strategy_form.html"
    list_display = ('name', 'strategy_cls', 'total_amount', 'available_amount', 'position_value', 'profit', 'fee',
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
            kwargs['choices'] = StrategyConfig.STRATEGY_TYPE_CHOICE

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
                pre = trader_cls.split('|')[1].lower()
                fixed_fields = ['id', 'name', 'strategy_cls', 'total_amount', 'data_source', 'trade', 'status',
                                'end_time', 'created_time', 'run_data']
                fields = [f.name for f in StrategyConfig._meta.get_fields() if f.name not in fixed_fields]
                fields_to_show = [f for f in fields if f.startswith(pre)]
                fields_to_hide = [f for f in fields if not f.startswith(pre)]

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
                # todo 从数据取
                'datasource_channel_choice': DataSourceConfig.CHANNEL_CHOICE,
                'datasource_symbol_choice': ["BTCUSDT", "ETHUSDT", "TRBUSDT", "ARBUSDT", "DOGESDT"],
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

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

    def get_queryset(self, request):
        return super().get_queryset(request).using("trade")


class KlineIntervalFilter(admin.SimpleListFilter):
    title = '周期'
    parameter_name = 'interval'

    def lookups(self, request, model_admin):
        return DataSourceConfig.CHANNEL_CHOICE

    def queryset(self, request, queryset):
        if self.value() is None:
            self.used_parameters.setdefault(self.parameter_name, "1m")


class KlineAdmin(ImportExportModelAdmin):
    list_display = ('symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount',)
    list_display_links = ('symbol',)
    sortable_by = ('timestamp desc',)
    list_filter = (KlineIntervalFilter, 'symbol', 'timestamp',)
    list_per_page = 10

    def get_queryset(self, request):
        return super().get_queryset(request).using(request.GET.get("interval", "1m"))


admin.site.register(TradeConfig, TradeConfigAdmin)
admin.site.register(DataSourceConfig, DataSourceConfigAdmin)
admin.site.register(StrategyConfig, StrategyConfigAdmin)
admin.site.register(TradeLog, TradeLogAdmin)
admin.site.register(Kline, KlineAdmin)
admin.site.site_header = '韭 量'
admin.site.site_title = ' 韭 量'
admin.site.index_title = ' 韭 量'
