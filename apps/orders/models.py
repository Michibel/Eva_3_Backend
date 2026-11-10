"""
Modelos de pedidos, cotizaciones y pagos para Dulce Arte
Incluye escalado BOM automático por porciones (12, 20, 40)
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.accounts.models import User
from apps.clients.models import Client
from apps.products.models import Product


class OrderStatus(models.TextChoices):
    COTIZACION = 'COTIZACION', _('Cotización')
    CONFIRMADO = 'CONFIRMADO', _('Confirmado')
    EN_PRODUCCION = 'EN_PRODUCCION', _('En Producción')
    LISTO = 'LISTO', _('Listo')
    DESPACHADO = 'DESPACHADO', _('Despachado')
    ENTREGADO = 'ENTREGADO', _('Entregado')
    CANCELADO = 'CANCELADO', _('Cancelado')


class PaymentMethod(models.TextChoices):
    WEBPAY = 'WEBPAY', _('WebPay')
    EFECTIVO = 'EFECTIVO', _('Efectivo')
    TRANSFERENCIA = 'TRANSFERENCIA', _('Transferencia')


class PaymentStatus(models.TextChoices):
    PENDIENTE = 'PENDIENTE', _('Pendiente')
    PAGADO_PARCIAL = 'PAGADO_PARCIAL', _('Pagado Parcial')
    PAGADO_TOTAL = 'PAGADO_TOTAL', _('Pagado Total')
    FALLIDO = 'FALLIDO', _('Fallido')
    REEMBOLSADO = 'REEMBOLSADO', _('Reembolsado')


class Order(models.Model):
    """Pedido principal"""
    OrderStatus = OrderStatus

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='orders', verbose_name=_('cliente'))
    status = models.CharField(_('estado'), max_length=20, choices=OrderStatus.choices, default=OrderStatus.COTIZACION)
    delivery_date = models.DateTimeField(_('fecha entrega'))
    delivery_address = models.TextField(_('dirección entrega'), blank=True)
    subtotal = models.DecimalField(_('subtotal'), max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(_('descuento'), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_('total'), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_('notas'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_orders', verbose_name=_('creado por'))
    confirmed_at = models.DateTimeField(_('confirmado en'), null=True, blank=True)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_orders', verbose_name=_('confirmado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('pedido')
        verbose_name_plural = _('pedidos')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'delivery_date']),
            models.Index(fields=['client', 'created_at']),
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.client.name} ({self.get_status_display()})"

    def calculate_totals(self):
        """Recalcula subtotal y total basado en items"""
        self.subtotal = sum(item.subtotal for item in self.items.all())
        self.total = self.subtotal - self.discount
        self.save()

    def confirm(self, user=None):
        """Confirma pedido: valida stock, descuenta BOM escalado, cambia estado"""
        from django.utils import timezone
        from apps.products.models import Product

        if self.status != OrderStatus.COTIZACION:
            raise ValueError('Solo se pueden confirmar pedidos en estado Cotización')

        # Validar stock para todos los items
        all_shortages = []
        for item in self.items.all():
            has_stock, shortages = item.product.check_stock_for_servings(item.servings, item.quantity)
            if not has_stock:
                for s in shortages:
                    s['order_item'] = item.id
                    s['product'] = item.product.name
                all_shortages.extend(shortages)

        if all_shortages:
            raise ValueError(f'Stock insuficiente: {all_shortages}')

        # Descontar stock escalado
        for item in self.items.all():
            item.product.consume_stock_for_servings(
                target_servings=item.servings,
                quantity=item.quantity,
                user=user,
                reference=f'Pedido #{self.id} - Item #{item.id}',
            )
            # Guardar snapshot del BOM escalado
            item.bom_snapshot_scaled = item.product.get_scaled_bom(item.servings)
            item.save()

        self.status = OrderStatus.CONFIRMADO
        self.confirmed_at = timezone.now()
        self.confirmed_by = user
        self.save()

        return True


class OrderItem(models.Model):
    """Item de pedido con porciones específicas (12, 20, 40)"""
    SERVINGS_CHOICES = [
        (12, '12 personas'),
        (20, '20 personas'),
        (40, '40 personas'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_('pedido'))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items', verbose_name=_('producto'))
    quantity = models.PositiveIntegerField(_('cantidad'), default=1)
    servings = models.PositiveIntegerField(_('porciones'), choices=SERVINGS_CHOICES, default=12)
    unit_price = models.DecimalField(_('precio unitario'), max_digits=10, decimal_places=2)
    custom_notes = models.TextField(_('notas personalizadas'), blank=True)
    bom_snapshot_scaled = models.JSONField(_('BOM escalado snapshot'), default=list, blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('item de pedido')
        verbose_name_plural = _('items de pedido')
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x{self.quantity} ({self.servings} porc.)"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def scaled_bom(self):
        """Retorna BOM escalado para este item"""
        if self.bom_snapshot_scaled:
            return self.bom_snapshot_scaled
        return self.product.get_scaled_bom(self.servings)

    def check_stock(self):
        """Verifica stock para este item"""
        return self.product.check_stock_for_servings(self.servings, self.quantity)


class Payment(models.Model):
    """Pago asociado a un pedido"""
    PaymentMethod = PaymentMethod
    PaymentStatus = PaymentStatus

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name=_('pedido'))
    amount = models.DecimalField(_('monto'), max_digits=10, decimal_places=2)
    method = models.CharField(_('método'), max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(_('estado'), max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDIENTE)
    transaction_id = models.CharField(_('ID transacción'), max_length=100, blank=True)
    notes = models.TextField(_('notas'), blank=True)
    paid_at = models.DateTimeField(_('pagado en'), null=True, blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('pago')
        verbose_name_plural = _('pagos')
        ordering = ['-created_at']

    def __str__(self):
        return f"Pago #{self.id} - Pedido #{self.order_id}: {self.amount} ({self.get_status_display()})"


class Quotation(models.Model):
    """Cotización preliminar"""
    STATUS_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADA', 'Enviada'),
        ('ACEPTADA', 'Aceptada'),
        ('RECHAZADA', 'Rechazada'),
        ('EXPIRADA', 'Expirada'),
    ]

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='quotations', verbose_name=_('cliente'))
    items = models.JSONField(_('items'), default=list)  # [{product_id, quantity, servings, unit_price, custom_notes}]
    valid_until = models.DateField(_('válida hasta'))
    status = models.CharField(_('estado'), max_length=20, choices=STATUS_CHOICES, default='BORRADOR')
    subtotal = models.DecimalField(_('subtotal'), max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(_('descuento'), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_('total'), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_('notas'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_quotations', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('cotización')
        verbose_name_plural = _('cotizaciones')
        ordering = ['-created_at']

    def __str__(self):
        return f"Cotización #{self.id} - {self.client.name} ({self.get_status_display()})"

    def calculate_totals(self):
        self.subtotal = sum(item.get('unit_price', 0) * item.get('quantity', 0) for item in self.items)
        self.total = self.subtotal - self.discount
        self.save()

    def convert_to_order(self, user=None):
        """Convierte cotización en pedido"""
        from django.utils import timezone
        order = Order.objects.create(
            client=self.client,
            status=OrderStatus.COTIZACION,
            delivery_date=timezone.now() + timezone.timedelta(days=7),
            delivery_address=self.client.address,
            subtotal=self.subtotal,
            discount=self.discount,
            total=self.total,
            notes=self.notes,
            created_by=user,
        )
        for item_data in self.items:
            product = Product.objects.get(id=item_data['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                servings=item_data.get('servings', 12),
                unit_price=item_data['unit_price'],
                custom_notes=item_data.get('custom_notes', ''),
            )
        self.status = 'ACEPTADA'
        self.save()
        return order