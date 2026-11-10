"""
Admin para producción Kanban
"""
from django.contrib import admin
from .models import KanbanColumn, ProductionCard, CardMovement


@admin.register(KanbanColumn)
class KanbanColumnAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'color', 'is_final']
    list_editable = ['order', 'color', 'is_final']
    ordering = ['order']


@admin.register(ProductionCard)
class ProductionCardAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'column', 'assigned_to', 'started_at', 'completed_at', 'waste_qty']
    list_filter = ['column', 'assigned_to']
    search_fields = ['order_item__product__name', 'order_item__order__client__name']
    autocomplete_fields = ['order_item', 'assigned_to']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CardMovement)
class CardMovementAdmin(admin.ModelAdmin):
    list_display = ['card', 'from_column', 'to_column', 'moved_by', 'moved_at']
    list_filter = ['from_column', 'to_column', 'moved_at']
    readonly_fields = ['moved_at']