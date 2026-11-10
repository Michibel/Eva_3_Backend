"""
Admin para productos y BOM
"""
from django.contrib import admin
from .models import Category, Product, ProductImage, BOMItem


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'order', 'alt_text']


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1
    fields = ['ingredient', 'quantity', 'unit', 'notes', 'order']
    autocomplete_fields = ['ingredient']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['order', 'name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_servings', 'base_price', 'sale_price', 'bom_calculated_cost', 'profit_margin', 'is_active']
    list_filter = ['category', 'base_servings', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['bom_calculated_cost', 'profit_margin', 'created_at', 'updated_at']
    autocomplete_fields = ['category']
    inlines = [ProductImageInline, BOMItemInline]
    ordering = ['category__order', 'name']

    fieldsets = (
        (None, {'fields': ('category', 'name', 'description', 'image')}),
        ('Precios y porciones', {'fields': ('base_price', 'sale_price', 'base_servings', 'prep_time_minutes')}),
        ('Costos calculados', {'fields': ('bom_calculated_cost', 'profit_margin'), 'classes': ('collapse',)}),
        ('Estado', {'fields': ('is_active',)}),
    )


@admin.register(BOMItem)
class BOMItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'ingredient', 'quantity', 'unit', 'order']
    list_filter = ['product__category', 'unit']
    search_fields = ['product__name', 'ingredient__name']
    autocomplete_fields = ['product', 'ingredient']
    ordering = ['product', 'order']