"""
Modelos de despacho y rutas para Dulce Arte
Confirmación de entrega con firma digital y foto
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.orders.models import Order


class Driver(models.Model):
    """Conductor/Repartidor"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile', verbose_name=_('usuario'))
    license_number = models.CharField(_('licencia de conducir'), max_length=50)
    phone = models.CharField(_('teléfono'), max_length=20)
    vehicle = models.CharField(_('vehículo'), max_length=100, blank=True)
    license_expiry = models.DateField(_('vencimiento licencia'), null=True, blank=True)
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('conductor')
        verbose_name_plural = _('conductores')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.license_number})"


class Route(models.Model):
    """Ruta de despacho"""
    STATUS_CHOICES = [
        ('PROGRAMADA', 'Programada'),
        ('EN_CURSO', 'En Curso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    name = models.CharField(_('nombre'), max_length=100)
    date = models.DateField(_('fecha'))
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='routes', verbose_name=_('conductor'))
    status = models.CharField(_('estado'), max_length=20, choices=STATUS_CHOICES, default='PROGRAMADA')
    notes = models.TextField(_('notas'), blank=True)
    started_at = models.DateTimeField(_('iniciada en'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completada en'), null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_routes', verbose_name=_('creado por'))
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('ruta')
        verbose_name_plural = _('rutas')
        ordering = ['-date', 'name']

    def __str__(self):
        return f"{self.name} - {self.date} ({self.get_status_display()})"


class Dispatch(models.Model):
    """Despacho individual dentro de una ruta"""
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_RUTA', 'En Ruta'),
        ('ENTREGADO', 'Entregado'),
        ('FALLIDO', 'Fallido'),
        ('REPROGRAMADO', 'Reprogramado'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='dispatches', verbose_name=_('ruta'))
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='dispatches', verbose_name=_('pedido'))
    sequence = models.PositiveIntegerField(_('secuencia'), default=0)
    status = models.CharField(_('estado'), max_length=20, choices=STATUS_CHOICES, default='PENDIENTE')
    delivered_at = models.DateTimeField(_('entregado en'), null=True, blank=True)
    signature = models.ImageField(_('firma digital'), upload_to='dispatch/signatures/', blank=True, null=True)
    photo = models.ImageField(_('foto comprobante'), upload_to='dispatch/photos/', blank=True, null=True)
    gps_lat = models.DecimalField(_('GPS Latitud'), max_digits=10, decimal_places=7, null=True, blank=True)
    gps_lng = models.DecimalField(_('GPS Longitud'), max_digits=10, decimal_places=7, null=True, blank=True)
    notes = models.TextField(_('notas'), blank=True)
    failure_reason = models.TextField(_('motivo fallo'), blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('despacho')
        verbose_name_plural = _('despachos')
        ordering = ['route', 'sequence']
        unique_together = ['route', 'sequence']

    def __str__(self):
        return f"{self.route.name} - #{self.sequence}: {self.order.client.name}"

    @property
    def client_name(self):
        return self.order.client.name

    @property
    def delivery_address(self):
        return self.order.delivery_address or self.order.client.address

    @property
    def total_amount(self):
        return self.order.total