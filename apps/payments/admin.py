"""
Admin para WebPay
"""
from django.contrib import admin
from .models import WebPayTransaction


@admin.register(WebPayTransaction)
class WebPayTransactionAdmin(admin.ModelAdmin):
    list_display = ['buy_order', 'order', 'amount', 'status', 'response_code', 'authorization_code', 'created_at']
    list_filter = ['status', 'response_code', 'created_at']
    search_fields = ['buy_order', 'session_id', 'order__id', 'authorization_code']
    readonly_fields = ['buy_order', 'session_id', 'amount', 'token', 'response_code', 'authorization_code',
                       'payment_type_code', 'installments_number', 'response_json', 'return_url', 'final_url',
                       'created_at', 'confirmed_at']
    autocomplete_fields = ['order', 'payment']