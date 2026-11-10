"""
Admin para despacho y rutas
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Driver, Route, Dispatch


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['user', 'license_number', 'phone', 'vehicle', 'license_expiry', 'is_active']
    list_filter = ['is_active']
    search_fields = ['user__first_name', 'user__last_name', 'license_number']
    autocomplete_fields = ['user']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'driver', 'status', 'dispatches_count', 'started_at', 'completed_at']
    list_filter = ['status', 'date', 'driver']
    search_fields = ['name', 'driver__user__first_name', 'driver__user__last_name']
    autocomplete_fields = ['driver', 'created_by']
    readonly_fields = ['created_at', 'updated_at']

    def dispatches_count(self, obj):
        return obj.dispatches.count()
    dispatches_count.short_description = 'Despachos'


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ['route', 'sequence', 'order', 'client_name', 'status', 'delivered_at', 'has_signature', 'has_photo']
    list_filter = ['status', 'route__date', 'route__driver']
    search_fields = ['route__name', 'order__client__name', 'order__id']
    autocomplete_fields = ['route', 'order']
    readonly_fields = ['created_at', 'updated_at', 'delivered_at', 'signature_preview', 'photo_preview']

    def client_name(self, obj):
        return obj.client_name
    client_name.short_description = 'Cliente'

    def has_signature(self, obj):
        return bool(obj.signature)
    has_signature.boolean = True
    has_signature.short_description = 'Firma'

    def has_photo(self, obj):
        return bool(obj.photo)
    has_photo.boolean = True
    has_photo.short_description = 'Foto'

    def signature_preview(self, obj):
        if obj.signature:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.signature.url)
        return '-'
    signature_preview.short_description = 'Firma'

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 200px;" />', obj.photo.url)
        return '-'
    photo_preview.short_description = 'Foto comprobante'