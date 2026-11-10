"""
Modelos de reportes para Dulce Arte
Dashboards, exportaciones y métricas
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Report(models.Model):
    """Reportes generados"""
    REPORT_TYPES = [
        ('VENTAS', 'Ventas por período'),
        ('STOCK', 'Stock crítico'),
        ('PRODUCCION', 'Producción por estado'),
        ('RENTABILIDAD', 'Rentabilidad por producto'),
        ('CLIENTES', 'Top clientes'),
        ('DESPACHOS', 'Despachos y entregas'),
    ]

    FORMAT_CHOICES = [
        ('JSON', 'JSON'),
        ('EXCEL', 'Excel'),
        ('PDF', 'PDF'),
    ]

    name = models.CharField(_('nombre'), max_length=100)
    report_type = models.CharField(_('tipo'), max_length=20, choices=REPORT_TYPES)
    format = models.CharField(_('formato'), max_length=10, choices=FORMAT_CHOICES, default='JSON')
    filters = models.JSONField(_('filtros'), default=dict, blank=True)
    file = models.FileField(_('archivo'), upload_to='reports/', blank=True, null=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_reports', verbose_name=_('generado por'))
    generated_at = models.DateTimeField(_('generado en'), auto_now_add=True)
    expires_at = models.DateTimeField(_('expira en'), null=True, blank=True)

    class Meta:
        verbose_name = _('reporte')
        verbose_name_plural = _('reportes')
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.generated_at.strftime('%d/%m/%Y %H:%M')}"


class DashboardWidget(models.Model):
    """Widgets personalizables para dashboard por rol"""
    WIDGET_TYPES = [
        ('KPI', 'Indicador KPI'),
        ('CHART_LINE', 'Gráfico de línea'),
        ('CHART_BAR', 'Gráfico de barras'),
        ('CHART_PIE', 'Gráfico de pastel'),
        ('TABLE', 'Tabla'),
        ('LIST', 'Lista'),
    ]

    name = models.CharField(_('nombre'), max_length=100)
    widget_type = models.CharField(_('tipo'), max_length=20, choices=WIDGET_TYPES)
    roles = models.JSONField(_('roles'), default=list, help_text=_('Roles que pueden ver este widget'))
    config = models.JSONField(_('configuración'), default=dict, help_text=_('Configuración del widget (query, colores, etc.)'))
    order = models.PositiveIntegerField(_('orden'), default=0)
    is_active = models.BooleanField(_('activo'), default=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('widget de dashboard')
        verbose_name_plural = _('widgets de dashboard')
        ordering = ['order']

    def __str__(self):
        return self.name