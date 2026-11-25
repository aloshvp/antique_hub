from django.contrib import admin
from .models import PurchaseMaster, Purchase, Cart


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('cartid', 'buyer', 'item', 'quantity', 'added_date')
    search_fields = ('buyer__username', 'item__title')
    list_filter = ('added_date',)


class PurchaseInline(admin.TabularInline):
    model = Purchase
    extra = 0
    readonly_fields = ('item', 'quantity')


@admin.register(PurchaseMaster)
class PurchaseMasterAdmin(admin.ModelAdmin):
    list_display = ('purchaseid', 'buyer', 'tot_amt', 'ship_charge', 'status', 'pay_status', 'purdate')
    list_filter = ('status', 'pay_status', 'purdate')
    search_fields = ('purchaseid', 'buyer__username', 'buyer__email')
    ordering = ('-purdate',)
    readonly_fields = ('purdate',)
    inlines = [PurchaseInline]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('pid', 'purchase_master', 'item', 'quantity')
    list_filter = ('purchase_master__status',)
    search_fields = ('item__title', 'purchase_master__purchaseid')
    ordering = ('-pid',)
