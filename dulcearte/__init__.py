"""
Dulce Arte - Sistema de Trazabilidad y Pedidos para Pastelería Artesanal
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de settings según entorno
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'local')

if ENVIRONMENT == 'production':
    from .settings.production import *
else:
    from .settings.local import *

# Aplicar configuración de base de datos
if 'postgresql' in DATABASES['default'].get('ENGINE', ''):
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
    }

# Compatibilidad Python 3.14 con BaseContext copy en Django 4.2
import django.template.context as _django_ctx
def _base_context_copy(self):
    duplicate = object.__new__(self.__class__)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate
_django_ctx.BaseContext.__copy__ = _base_context_copy