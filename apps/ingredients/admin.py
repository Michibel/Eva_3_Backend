"""
Admin para ingredientes, stock y compras
"""
from django.contrib import admin
from .models import Supplier, Ingredient, StockMovement, PurchaseOrder, PurchaseOrderItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'contact', 'email']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'current_stock', 'min_stock', 'unit_cost', 'stock_status', 'supplier', 'is_active']
    list_filter = ['unit', 'is_perishable', 'is_active', 'supplier']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['supplier']

    def stock_status(self, obj):
        status_colors = {
            'SIN_STOCK': 'red',
            'BAJO_STOCK': 'orange',
            'OK': 'green',
        }
        color = status_colors.get(obj.stock_status, 'black')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_stock_status_display())

    stock_status.short_description = 'Estado Stock'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['ingredient', 'type', 'quantity', 'reference', 'created_by', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['ingredient__name', 'reference']
    readonly_fields = ['created_at']
    autocomplete_fields = ['ingredient', 'created_by']
    ordering = ['-created_at']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    autocomplete_fields = ['ingredient']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'expected_date', 'status', 'total', 'created_at']
    list_filter = ['status', 'expected_date']
    search_fields = ['supplier__name']
    readonly_fields = ['total', 'created_at', 'updated_at']
    autocomplete_fields = ['supplier', 'created_by']
    inlines = [PurchaseOrderItemInline]