from django.contrib import admin
from .models import Stock, Discount


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('stockid', 'item', 'cur_stock', 'tot_arr_stock', 'status', 'stockdate')
    list_filter = ('status', 'stockdate')
    search_fields = ('item__title', 'item__item')
    ordering = ('-stockdate',)
    readonly_fields = ('stockdate',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('discountid', 'applicable_cat', 'discount_percent', 'startdate', 'enddate')
    list_filter = ('applicable_cat', 'startdate', 'enddate')
    search_fields = ('applicable_cat__category',)
    ordering = ('-startdate',)
