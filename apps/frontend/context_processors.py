"""
Context processors para frontend
"""
from django.conf import settings
from django.db import models


def user_role(request):
    """Agrega información del rol del usuario al contexto de templates"""
    context = {
        'user_role': None,
        'user_role_display': '',
        'is_staff_member': False,
        'WEBPAY_COMMERCE_CODE': getattr(settings, 'WEBPAY_COMMERCE_CODE', ''),
    }

    if request.user.is_authenticated:
        context['user_role'] = request.user.role
        context['user_role_display'] = request.user.get_role_display()
        context['is_staff_member'] = request.user.is_staff_member()

    return context


def low_stock_count(request):
    """Agrega el conteo de insumos con stock bajo al contexto"""
    context = {'low_stock_count': 0}

    if request.user.is_authenticated and request.user.is_staff_member():
        try:
            from apps.ingredients.models import Ingredient
            context['low_stock_count'] = Ingredient.objects.filter(
                current_stock__lte=models.F('min_stock'),
                is_active=True
            ).count()
        except Exception:
            pass

    return context