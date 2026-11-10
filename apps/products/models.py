"""
Modelos de productos/recetas y BOM para Dulce Arte
Escalado automático por porciones: 12, 20, 40 personas
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.ingredients.models import Ingredient


class Category(models.Model):
    """Categoría de producto (tortas, pasteles, galletas, etc.)"""
    name = models.CharField(_('nombre'), max_length=100, unique=True)
    description = models.TextField(_('descripción'), blank=True)
    order = models.PositiveIntegerField(_('orden'), default=0)
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('categoría')
        verbose_name_plural = _('categorías')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Producto/Receta base con BOM para porciones base (default 12)"""
    SERVINGS_CHOICES = [
        (12, '12 personas'),
        (20, '20 personas'),
        (40, '40 personas'),
    ]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name=_('categoría'))
    name = models.CharField(_('nombre'), max_length=200)
    description = models.TextField(_('descripción'), blank=True)
    image = models.ImageField(_('imagen'), upload_to='products/', blank=True, null=True)
    base_price = models.DecimalField(_('precio base'), max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField(_('precio venta'), max_digits=10, decimal_places=2, default=0)
    prep_time_minutes = models.PositiveIntegerField(_('tiempo preparación (min)'), default=60)
    base_servings = models.PositiveIntegerField(
        _('porciones base'),
        choices=SERVINGS_CHOICES,
        default=12,
        help_text=_('Porciones para las que está definida la receta base (BOM)')
    )
    is_active = models.BooleanField(_('activo'), default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_products', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('producto/receta')
        verbose_name_plural = _('productos/recetas')
        ordering = ['category__order', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.base_servings} porciones)"

    @property
    def bom_calculated_cost(self):
        """Costo calculado del BOM para porciones base"""
        total = 0
        for bom_item in self.bom_items.select_related('ingredient').all():
            total += bom_item.quantity * bom_item.ingredient.unit_cost
        return total

    @property
    def profit_margin(self):
        """Margen de ganancia basado en precio venta vs costo BOM"""
        if self.bom_calculated_cost > 0:
            return ((self.sale_price - self.bom_calculated_cost) / self.sale_price) * 100
        return 0

    def get_scaled_bom(self, target_servings):
        """
        Retorna el BOM escalado para las porciones objetivo.
        Retorna lista de dicts con ingredient, quantity, unit, estimated_cost
        """
        from decimal import Decimal

        if target_servings == self.base_servings:
            scale_factor = Decimal('1')
        else:
            scale_factor = Decimal(str(target_servings)) / Decimal(str(self.base_servings))

        scaled = []
        for bom_item in self.bom_items.select_related('ingredient').all():
            scaled_qty = round(bom_item.quantity * scale_factor, 3)
            scaled.append({
                'ingredient_id': bom_item.ingredient_id,
                'ingredient_name': bom_item.ingredient.name,
                'ingredient_unit': bom_item.ingredient.unit,
                'base_quantity': float(bom_item.quantity),
                'scaled_quantity': float(scaled_qty),
                'unit': bom_item.unit,
                'unit_cost': float(bom_item.ingredient.unit_cost),
                'estimated_cost': round(float(bom_item.ingredient.unit_cost) * float(scaled_qty), 2),
                'notes': bom_item.notes,
            })
        return scaled

    def check_stock_for_servings(self, target_servings, quantity=1):
        """
        Verifica si hay stock suficiente para producir 'quantity' unidades
        del producto con 'target_servings' porciones cada una.
        Retorna (bool, list_shortages)
        """
        from decimal import Decimal

        scale_factor = Decimal(str(target_servings)) / Decimal(str(self.base_servings))
        shortages = []

        for bom_item in self.bom_items.select_related('ingredient').all():
            needed = bom_item.quantity * scale_factor * quantity
            available = bom_item.ingredient.current_stock
            if available < needed:
                shortages.append({
                    'ingredient': bom_item.ingredient.name,
                    'needed': round(needed, 3),
                    'available': float(available),
                    'unit': bom_item.ingredient.unit,
                    'shortage': round(needed - available, 3),
                })

        return len(shortages) == 0, shortages

    def consume_stock_for_servings(self, target_servings, quantity=1, user=None, reference=None):
        """
        Descuenta stock escalado para producción.
        Crea StockMovement de tipo SALIDA.
        """
        from decimal import Decimal
        from apps.ingredients.models import StockMovement

        scale_factor = Decimal(str(target_servings)) / Decimal(str(self.base_servings))

        for bom_item in self.bom_items.select_related('ingredient').all():
            qty_to_consume = round(bom_item.quantity * scale_factor * quantity, 3)
            ingredient = bom_item.ingredient

            # Descontar stock
            ingredient.current_stock -= qty_to_consume
            ingredient.save()

            # Registrar movimiento
            StockMovement.objects.create(
                ingredient=ingredient,
                type='SALIDA',
                quantity=qty_to_consume,
                reference=reference or f'Producción {self.name} x{quantity} ({target_servings} porc.)',
                notes=f'BOM escalado desde {self.base_servings} a {target_servings} porciones',
                created_by=user,
            )


class ProductImage(models.Model):
    """Imágenes adicionales del producto"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name=_('producto'))
    image = models.ImageField(_('imagen'), upload_to='products/gallery/')
    order = models.PositiveIntegerField(_('orden'), default=0)
    alt_text = models.CharField(_('texto alternativo'), max_length=200, blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)

    class Meta:
        verbose_name = _('imagen de producto')
        verbose_name_plural = _('imágenes de productos')
        ordering = ['order']


class BOMItem(models.Model):
    """Item de la Lista de Materiales (Bill of Materials) - Receta desglosada"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bom_items', verbose_name=_('producto'))
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name='bom_items', verbose_name=_('ingrediente'))
    quantity = models.DecimalField(_('cantidad'), max_digits=10, decimal_places=3, help_text=_('Cantidad para porciones base'))
    unit = models.CharField(_('unidad'), max_length=20, help_text=_('Unidad de medida (kg, g, l, ml, un)'))
    notes = models.TextField(_('notas'), blank=True)
    order = models.PositiveIntegerField(_('orden'), default=0)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('item BOM')
        verbose_name_plural = _('items BOM')
        ordering = ['order', 'ingredient__name']
        unique_together = ['product', 'ingredient']

    def __str__(self):
        return f"{self.product.name} - {self.ingredient.name}: {self.quantity} {self.unit}"