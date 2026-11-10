"""
Admin para clientes
"""
from django.contrib import admin
from .models import Client, ClientPreference


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'is_active', 'total_orders', 'total_spent', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_orders', 'total_spent']
    ordering = ['name']


@admin.register(ClientPreference)
class ClientPreferenceAdmin(admin.ModelAdmin):
    list_display = ['client', 'key', 'value', 'created_at']
    list_filter = ['key', 'created_at']
    search_fields = ['client__name', 'key']