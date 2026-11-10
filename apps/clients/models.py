"""
Modelos de clientes para Dulce Arte
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Client(models.Model):
    """Cliente de la pastelería"""
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='client_profile', verbose_name=_('usuario portal')
    )
    name = models.CharField(_('nombre'), max_length=200)
    email = models.EmailField(_('email'), unique=True)
    phone = models.CharField(_('teléfono'), max_length=20, blank=True)
    address = models.TextField(_('dirección'), blank=True)
    notes = models.TextField(_('notas'), blank=True)
    is_active = models.BooleanField(_('activo'), default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_clients', verbose_name=_('creado por')
    )
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('cliente')
        verbose_name_plural = _('clientes')
        ordering = ['name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_spent(self):
        from django.db.models import Sum
        return self.orders.filter(status__in=['ENTREGADO', 'DESPACHADO']).aggregate(
            total=Sum('total')
        )['total'] or 0

    @property
    def last_order_date(self):
        last_order = self.orders.order_by('-created_at').first()
        return last_order.created_at if last_order else None


class ClientPreference(models.Model):
    """Preferencias del cliente (alergias, sabores favoritos, etc.)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='preferences', verbose_name=_('cliente'))
    key = models.CharField(_('clave'), max_length=50)
    value = models.TextField(_('valor'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('preferencia de cliente')
        verbose_name_plural = _('preferencias de clientes')
        unique_together = ['client', 'key']

    def __str__(self):
        return f"{self.client.name} - {self.key}: {self.value}"