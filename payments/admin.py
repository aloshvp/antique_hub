from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payid', 'purchase_master', 'buyer', 'amount', 'method', 'bank_name', 'card_last4', 'status', 'pay_date')
    list_filter = ('status', 'method', 'pay_date')
    search_fields = ('transaction_ref', 'buyer__username', 'card_last4', 'bank_name')
    ordering = ('-pay_date',)
    readonly_fields = ('pay_date', 'transaction_ref', 'card_last4', 'card_type', 'bank_name')
