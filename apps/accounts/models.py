"""
Modelos de cuentas y usuarios para Dulce Arte
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = 'ADMIN', _('Administrador/Propietario')
    VENTAS = 'VENTAS', _('Ventas/Atención')
    COCINERO = 'COCINERO', _('Cocinero/Producción')
    BODEGA = 'BODEGA', _('Bodega/Insumos')
    REPARTIDOR = 'REPARTIDOR', _('Repartidor/Logística')
    CLIENTE = 'CLIENTE', _('Cliente (Portal)')


class User(AbstractUser):
    """Usuario personalizado con roles"""
    Role = Role
    email = models.EmailField(_('email'), unique=True)
    phone = models.CharField(_('teléfono'), max_length=20, blank=True)
    role = models.CharField(_('rol'), max_length=20, choices=Role.choices, default=Role.CLIENTE)
    is_verified = models.BooleanField(_('verificado'), default=False)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def has_role(self, *roles):
        return self.role in roles

    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_client(self):
        return self.role == Role.CLIENTE

    def is_staff_member(self):
        return self.role in [Role.ADMIN, Role.VENTAS, Role.COCINERO, Role.BODEGA, Role.REPARTIDOR]

    @property
    def client(self):
        return getattr(self, 'client_profile', None)

    @property
    def driver(self):
        return getattr(self, 'driver_profile', None)


class Profile(models.Model):
    """Perfil extendido del usuario"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('usuario'))
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    address = models.TextField(_('dirección'), blank=True)
    birth_date = models.DateField(_('fecha de nacimiento'), blank=True, null=True)
    preferences = models.JSONField(_('preferencias'), default=dict, blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)
    updated_at = models.DateTimeField(_('actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('perfil')
        verbose_name_plural = _('perfiles')

    def __str__(self):
        return f"Perfil de {self.user}"


class AuditLog(models.Model):
    """Log de auditoría para acciones importantes"""
    ACTION_CHOICES = [
        ('CREATE', 'Crear'),
        ('UPDATE', 'Actualizar'),
        ('DELETE', 'Eliminar'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Exportar'),
        ('STATUS_CHANGE', 'Cambio de estado'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('usuario'))
    action = models.CharField(_('acción'), max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(_('modelo'), max_length=50)
    object_id = models.CharField(_('ID objeto'), max_length=50)
    changes = models.JSONField(_('cambios'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    created_at = models.DateTimeField(_('creado'), auto_now_add=True)

    class Meta:
        verbose_name = _('log de auditoría')
        verbose_name_plural = _('logs de auditoría')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} - {self.model_name} #{self.object_id} by {self.user}"