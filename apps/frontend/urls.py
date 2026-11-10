"""
URLs para la app frontend (templates)
"""
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import (
    DashboardView, ClientsView, ProductsView, IngredientsView,
    OrdersView, ProductionView, DispatchView, PaymentsView,
    ReportsView, ClientPortalView, RegisterView, PasswordChangeView,
    CustomLoginView, CustomLogoutView
)

urlpatterns = [
    # Auth
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),

    # Dashboard principal
    path('', DashboardView.as_view(), name='dashboard'),

    # Módulos (requieren staff)
    path('clientes/', ClientsView.as_view(), name='clients'),
    path('productos/', ProductsView.as_view(), name='products'),
    path('insumos/', IngredientsView.as_view(), name='ingredients'),
    path('pedidos/', OrdersView.as_view(), name='orders'),
    path('produccion/', ProductionView.as_view(), name='production'),
    path('despachos/', DispatchView.as_view(), name='dispatch'),
    path('pagos/', PaymentsView.as_view(), name='payments'),
    path('reportes/', ReportsView.as_view(), name='reports'),

    # Portal cliente
    path('portal/', ClientPortalView.as_view(), name='client_portal'),
]