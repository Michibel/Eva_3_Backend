"""
URLs para la app payments
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebPayTransactionViewSet

router = DefaultRouter()
router.register(r'webpay-transactions', WebPayTransactionViewSet, basename='webpay-transaction')

urlpatterns = [
    path('', include(router.urls)),
]