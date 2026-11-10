"""
Admin para pedidos, items y pagos
"""
from django.contrib import admin
from .models import Order, OrderItem, Payment, Quotation, PaymentStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'quantity', 'servings', 'unit_price', 'custom_notes']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['product']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['amount', 'method', 'status', 'transaction_id', 'paid_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'status', 'delivery_date', 'total', 'payment_status', 'created_at']
    list_filter = ['status', 'delivery_date', 'created_at']
    search_fields = ['client__name', 'client__email', 'id']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at', 'confirmed_by']
    autocomplete_fields = ['client', 'created_by', 'confirmed_by']
    inlines = [OrderItemInline, PaymentInline]
    ordering = ['-created_at']

    def payment_status(self, obj):
        paid = sum(p.amount for p in obj.payments.filter(status=PaymentStatus.PAGADO_TOTAL))
        if paid >= obj.total:
            return 'Pagado'
        elif paid > 0:
            return f'Parcial ({paid}/{obj.total})'
        return 'Pendiente'
    payment_status.short_description = 'Estado Pago'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'quantity', 'servings', 'unit_price', 'subtotal']
    list_filter = ['servings', 'product__category']
    search_fields = ['order__id', 'product__name']
    autocomplete_fields = ['order', 'product']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'method', 'status', 'transaction_id', 'paid_at']
    list_filter = ['method', 'status', 'created_at']
    search_fields = ['order__id', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['order']


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'status', 'valid_until', 'total', 'created_at']
    list_filter = ['status', 'valid_until']
    search_fields = ['client__name', 'id']
    readonly_fields = ['created_at', 'updated_at', 'subtotal', 'total']
    autocomplete_fields = ['client', 'created_by']