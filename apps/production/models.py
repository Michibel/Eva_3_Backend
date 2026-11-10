"""
Modelos de producción Kanban para Dulce Arte
Estados: Recibido → En Preparación → Horneado/Decorado → Control Calidad → Listo
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.orders.models import OrderItem


class KanbanColumn(models.Model):
    """Columnas del tablero Kanban"""
    DEFAULT_COLUMNS = [
        ('RECIBIDO', 'Recibido', 1, '#6c757d'),
        ('EN_PREPARACION', 'En Preparación', 2, '#0d6efd'),
        ('HORNEADO_DECORADO', 'Horneado/Decorado', 3, '#fd7e14'),
        ('CONTROL_CALIDAD', 'Control de Calidad', 4, '#ffc107'),
        ('LISTO', 'Listo', 5, '#198754'),
    ]

    STATUS_CHOICES = [(code, name) for code, name, _, _ in DEFAULT_COLUMNS]

    name = models.CharField(_('nombre'), max_length=50, choices=STATUS_CHOICES, unique=True)
    order = models.PositiveIntegerField(_('orden'), default=0)
    color = models.CharField(_('color'), max_length=7, default='#6c757d')
    is_final = models.BooleanField(_('es final'), default=False)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)

    class Meta:
        verbose_name = _('columna Kanban')
        verbose_name_plural = _('columnas Kanban')
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.get_name_display()}"


class ProductionCard(models.Model):
    """Tarjeta de producción vinculada a OrderItem"""
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='production_card', verbose_name=_('item de pedido'))
    column = models.ForeignKey(KanbanColumn, on_delete=models.PROTECT, related_name='cards', verbose_name=_('columna'))
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cards', verbose_name=_('asignado a'))
    started_at = models.DateTimeField(_('iniciado en'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completado en'), null=True, blank=True)
    notes = models.TextField(_('notas'), blank=True)
    waste_qty = models.DecimalField(_('merma cantidad'), max_digits=8, decimal_places=3, default=0)
    waste_reason = models.TextField(_('motivo merma'), blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('tarjeta de producción')
        verbose_name_plural = _('tarjetas de producción')
        ordering = ['column__order', 'id']

    def __str__(self):
        return f"{self.order_item} - {self.column.get_name_display()}"

    @property
    def product_name(self):
        return self.order_item.product.name

    @property
    def servings(self):
        return self.order_item.servings

    @property
    def quantity(self):
        return self.order_item.quantity


class CardMovement(models.Model):
    """Historial de movimientos entre columnas"""
    card = models.ForeignKey(ProductionCard, on_delete=models.CASCADE, related_name='movements', verbose_name=_('tarjeta'))
    from_column = models.ForeignKey(KanbanColumn, on_delete=models.PROTECT, related_name='movements_from', verbose_name=_('desde columna'))
    to_column = models.ForeignKey(KanbanColumn, on_delete=models.PROTECT, related_name='movements_to', verbose_name=_('hacia columna'))
    moved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_movements', verbose_name=_('movido por'))
    moved_at = models.DateTimeField(_('movido en'), auto_now_add=True)
    notes = models.TextField(_('notas'), blank=True)

    class Meta:
        verbose_name = _('movimiento de tarjeta')
        verbose_name_plural = _('movimientos de tarjetas')
        ordering = ['-moved_at']

    def __str__(self):
        return f"{self.card} : {self.from_column} → {self.to_column}"