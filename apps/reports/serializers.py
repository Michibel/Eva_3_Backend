"""
Serializers para reportes y dashboard
"""
from rest_framework import serializers
from .models import Report, DashboardWidget


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = ['id', 'name', 'widget_type', 'roles', 'config', 'order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'name', 'report_type', 'format', 'filters', 'file', 'generated_by', 'generated_by_name', 'generated_at', 'expires_at']
        read_only_fields = ['generated_at']


class ReportGenerateSerializer(serializers.Serializer):
    """Serializer para generar reporte"""
    report_type = serializers.ChoiceField(choices=Report.REPORT_TYPES)
    format = serializers.ChoiceField(choices=Report.FORMAT_CHOICES, default='JSON')
    filters = serializers.DictField(required=False, default=dict)