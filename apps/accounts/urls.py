"""
URLs para la app accounts
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet, AuditLogViewSet, GetJWTTokensView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
    path('jwt-tokens/', GetJWTTokensView.as_view(), name='get-jwt-tokens'),
]