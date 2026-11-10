"""
URLs para la app reports
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DashboardWidgetViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'dashboard-widgets', DashboardWidgetViewSet, basename='dashboard-widget')
router.register(r'', ReportViewSet, basename='report')

urlpatterns = [
    path('dashboard/', ReportViewSet.as_view({'get': 'dashboard'}), name='dashboard'),
    path('generate/', ReportViewSet.as_view({'post': 'generate'}), name='report-generate'),
    path('<str:report_type>/export/', ReportViewSet.as_view({'get': 'export_report'}), name='report-export'),
    path('', include(router.urls)),
]