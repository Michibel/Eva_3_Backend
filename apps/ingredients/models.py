"""
Modelos de ingredientes/insumos, stock y compras para Dulce Arte
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Supplier(models.Model):
    """Proveedor de insumos"""
    name = models.CharField(_('nombre'), max_length=200)
    contact = models.CharField(_('contacto'), max_length=100, blank=True)
    phone = models.CharField(_('teléfono'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    address = models.TextField(_('dirección'), blank=True)
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('proveedor')
        verbose_name_plural = _('proveedores')
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Ingrediente/Insumo con stock y alertas"""
    UNIT_CHOICES = [
        ('kg', 'Kilogramos (kg)'),
        ('g', 'Gramos (g)'),
        ('l', 'Litros (l)'),
        ('ml', 'Mililitros (ml)'),
        ('un', 'Unidades (un)'),
        ('docena', 'Docenas'),
    ]

    name = models.CharField(_('nombre'), max_length=200)
    unit = models.CharField(_('unidad'), max_length=20, choices=UNIT_CHOICES)
    current_stock = models.DecimalField(_('stock actual'), max_digits=10, decimal_places=3, default=0)
    min_stock = models.DecimalField(_('stock mínimo'), max_digits=10, decimal_places=3, default=0)
    unit_cost = models.DecimalField(_('costo unitario'), max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingredients', verbose_name=_('proveedor'))
    is_perishable = models.BooleanField(_('perecible'), default=False)
    shelf_life_days = models.PositiveIntegerField(_('vida útil (días)'), blank=True, null=True)
    is_active = models.BooleanField(_('activo'), default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_ingredients', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('ingrediente/insumo')
        verbose_name_plural = _('ingredientes/insumos')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['current_stock']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.unit})"

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock

    @property
    def movements(self):
        return self.stock_movements.all()

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'SIN_STOCK'
        elif self.current_stock <= self.min_stock:
            return 'BAJO_STOCK'
        return 'OK'

    def add_stock(self, quantity, movement_type='ENTRADA', reference='', notes='', user=None):
        """Agrega stock y registra movimiento"""
        from .models import StockMovement
        self.current_stock += quantity
        self.save()
        StockMovement.objects.create(
            ingredient=self,
            type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=user,
        )

    def remove_stock(self, quantity, movement_type='SALIDA', reference='', notes='', user=None):
        """Quita stock y registra movimiento"""
        from .models import StockMovement
        if self.current_stock < quantity:
            raise ValueError(f"Stock insuficiente. Disponible: {self.current_stock} {self.unit}")
        self.current_stock -= quantity
        self.save()
        StockMovement.objects.create(
            ingredient=self,
            type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=user,
        )


class StockMovement(models.Model):
    """Movimiento de stock (entrada, salida, merma, ajuste)"""
    TYPE_CHOICES = [
        ('ENTRADA', 'Entrada/Compra'),
        ('SALIDA', 'Salida/Producción'),
        ('MERMA', 'Merma/Pérdida'),
        ('AJUSTE', 'Ajuste/Inventario'),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='stock_movements', verbose_name=_('ingrediente'))
    type = models.CharField(_('tipo'), max_length=10, choices=TYPE_CHOICES)
    quantity = models.DecimalField(_('cantidad'), max_digits=10, decimal_places=3)
    reference = models.CharField(_('referencia'), max_length=200, blank=True)
    notes = models.TextField(_('notas'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)

    class Meta:
        verbose_name = _('movimiento de stock')
        verbose_name_plural = _('movimientos de stock')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ingredient', 'created_at']),
            models.Index(fields=['type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.ingredient.name}: {self.quantity} {self.ingredient.unit}"


class PurchaseOrder(models.Model):
    """Orden de compra a proveedores"""
    STATUS_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADA', 'Enviada'),
        ('CONFIRMADA', 'Confirmada'),
        ('RECIBIDA', 'Recibida'),
        ('CANCELADA', 'Cancelada'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders', verbose_name=_('proveedor'))
    expected_date = models.DateField(_('fecha esperada'))
    status = models.CharField(_('estado'), max_length=20, choices=STATUS_CHOICES, default='BORRADOR')
    total = models.DecimalField(_('total'), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_('notas'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_purchase_orders', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('orden de compra')
        verbose_name_plural = _('órdenes de compra')
        ordering = ['-created_at']

    def __str__(self):
        return f"OC-{self.id:06d} - {self.supplier.name}"

    def update_total(self):
        self.total = sum(item.subtotal for item in self.items.all())
        self.save()


class PurchaseOrderItem(models.Model):
    """Item de orden de compra"""
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name=_('orden'))
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name='purchase_order_items', verbose_name=_('ingrediente'))
    quantity = models.DecimalField(_('cantidad'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('costo unitario'), max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(_('cantidad recibida'), max_digits=10, decimal_places=3, default=0)
    notes = models.TextField(_('notas'), blank=True)

    class Meta:
        verbose_name = _('item de orden de compra')
        verbose_name_plural = _('items de orden de compra')
        unique_together = ['order', 'ingredient']

    def __str__(self):
        return f"{self.order} - {self.ingredient.name}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost

    def receive(self, quantity, user=None):
        """Recibe cantidad y actualiza stock"""
        from decimal import Decimal
        quantity = Decimal(str(quantity))
        self.received_quantity += quantity
        self.save()
        self.ingredient.add_stock(
            quantity=quantity,
            movement_type='ENTRADA',
            reference=f'Recepción OC-{self.order.id:06d}',
            notes=f'Item: {self.ingredient.name}',
            user=user,
        )
        # Actualizar estado de la OC
        if all(item.received_quantity >= item.quantity for item in self.order.items.all()):
            self.order.status = 'RECIBIDA'
            self.order.save()