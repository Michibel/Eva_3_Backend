"""
Modelos de pagos y WebPay para Dulce Arte
Integración con Transbank WebPay Plus (sandbox/producción)
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.orders.models import Order, Payment


class WebPayTransaction(models.Model):
    """Transacción WebPay para trazabilidad completa"""
    STATUS_CHOICES = [
        ('INICIADA', 'Iniciada'),
        ('AUTORIZADA', 'Autorizada'),
        ('RECHAZADA', 'Rechazada'),
        ('ANULADA', 'Anulada'),
        ('ERROR', 'Error'),
    ]

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='webpay_transactions', verbose_name=_('pedido'))
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name='webpay_transaction', null=True, blank=True, verbose_name=_('pago'))

    # Datos de la transacción
    buy_order = models.CharField(_('orden de compra'), max_length=50, unique=True)
    session_id = models.CharField(_('ID sesión'), max_length=50)
    amount = models.DecimalField(_('monto'), max_digits=10, decimal_places=2)
    status = models.CharField(_('estado'), max_length=20, choices=STATUS_CHOICES, default='INICIADA')

    # Respuesta de WebPay
    token = models.CharField(_('token'), max_length=100, blank=True)
    response_code = models.IntegerField(_('código respuesta'), null=True, blank=True)
    authorization_code = models.CharField(_('código autorización'), max_length=20, blank=True)
    payment_type_code = models.CharField(_('tipo pago'), max_length=10, blank=True)
    installments_number = models.IntegerField(_('cuotas'), null=True, blank=True)
    response_json = models.JSONField(_('respuesta completa'), default=dict, blank=True)

    # URLs
    return_url = models.URLField(_('URL retorno'), blank=True)
    final_url = models.URLField(_('URL final'), blank=True)

    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    confirmed_at = models.DateTimeField(_('confirmado en'), null=True, blank=True)

    class Meta:
        verbose_name = _('transacción WebPay')
        verbose_name_plural = _('transacciones WebPay')
        ordering = ['-created_at']

    def __str__(self):
        return f"WebPay #{self.buy_order} - {self.get_status_display()} ({self.amount})"