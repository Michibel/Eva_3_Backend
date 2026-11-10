"""
URLs para la app dispatch
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DriverViewSet, RouteViewSet, DispatchViewSet

router = DefaultRouter()
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'dispatches', DispatchViewSet, basename='dispatch')

urlpatterns = [
    path('', include(router.urls)),
]