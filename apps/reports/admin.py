"""
Admin para reportes
"""
from django.contrib import admin
from .models import Report, DashboardWidget


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format', 'generated_by', 'generated_at', 'expires_at']
    list_filter = ['report_type', 'format', 'generated_at']
    search_fields = ['name', 'generated_by__username']
    readonly_fields = ['generated_at']
    autocomplete_fields = ['generated_by']


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'roles', 'order', 'is_active']
    list_filter = ['widget_type', 'is_active']
    list_editable = ['order', 'is_active']