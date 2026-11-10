"""
URLs para la app production
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KanbanColumnViewSet, ProductionCardViewSet, CardMovementViewSet

router = DefaultRouter()
router.register(r'kanban-columns', KanbanColumnViewSet, basename='kanban-column')
router.register(r'production-cards', ProductionCardViewSet, basename='production-card')
router.register(r'card-movements', CardMovementViewSet, basename='card-movement')

urlpatterns = [
    path('', include(router.urls)),
]