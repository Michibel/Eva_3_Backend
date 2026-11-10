"""
URLs para la app clients
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, ClientPreferenceViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'client-preferences', ClientPreferenceViewSet, basename='client-preference')

urlpatterns = [
    path('', include(router.urls)),
]