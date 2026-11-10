"""
Serializers para despacho y rutas
"""
import base64
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import Driver, Route, Dispatch
from apps.orders.serializers import OrderListSerializer


class Base64ImageField(serializers.ImageField):
    """Soporta imágenes subidas como data:image/...;base64,..."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                header, imgstr = data.split(';base64,')
                ext = header.split('/')[-1]
                if ext == 'jpeg':
                    ext = 'jpg'
                file_name = f"{uuid.uuid4().hex[:10]}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                raise serializers.ValidationError(f"Error decodificando imagen base64: {e}")
        return super().to_internal_value(data)


class DriverSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Driver
        fields = ['id', 'user', 'user_name', 'user_email', 'license_number', 'phone', 'vehicle', 'license_expiry', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class DispatchListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados en ruta"""
    order_detail = OrderListSerializer(source='order', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    client_name = serializers.CharField(source='order.client.name', read_only=True)
    delivery_address = serializers.CharField(source='order.delivery_address', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Dispatch
        fields = [
            'id', 'sequence', 'order', 'order_id', 'order_detail', 'client_name',
            'delivery_address', 'route_name', 'driver_name', 'status', 'delivered_at',
            'signature', 'photo', 'notes'
        ]

    def get_driver_name(self, obj):
        if obj.route and obj.route.driver and obj.route.driver.user:
            return obj.route.driver.user.get_full_name() or obj.route.driver.user.username
        return 'Sin conductor'


class RouteSerializer(serializers.ModelSerializer):
    driver_detail = DriverSerializer(source='driver', read_only=True)
    driver_name = serializers.SerializerMethodField()
    vehicle = serializers.CharField(source='driver.vehicle', read_only=True, default='')
    dispatches = DispatchListSerializer(many=True, read_only=True)
    dispatches_count = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Route
        fields = ['id', 'name', 'date', 'driver', 'driver_name', 'vehicle', 'driver_detail', 'status', 'notes',
                  'dispatches', 'dispatches_count', 'started_at', 'completed_at',
                  'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']

    def get_driver_name(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.get_full_name() or obj.driver.user.username
        return 'Sin conductor'


class RouteCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['name', 'date', 'driver', 'status', 'notes']


class DispatchSerializer(serializers.ModelSerializer):
    order_detail = OrderListSerializer(source='order', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)

    class Meta:
        model = Dispatch
        fields = ['id', 'route', 'route_name', 'order', 'order_detail', 'sequence', 'status',
                  'delivered_at', 'signature', 'photo', 'gps_lat', 'gps_lng',
                  'notes', 'failure_reason', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'delivered_at']


class DispatchDeliverSerializer(serializers.Serializer):
    """Serializer para confirmar entrega con firma y foto (soporta base64 y archivos multipart)"""
    signature = Base64ImageField(required=True)
    photo = Base64ImageField(required=False, allow_null=True)
    photo_base64 = Base64ImageField(required=False, allow_null=True, write_only=True)
    gps_lat = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    gps_lng = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('photo') and attrs.get('photo_base64'):
            attrs['photo'] = attrs.pop('photo_base64')
        elif 'photo_base64' in attrs:
            attrs.pop('photo_base64')
        return attrs

    def validate_signature(self, value):
        if value and value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('La firma no puede exceder 5MB.')
        return value

    def validate_photo(self, value):
        if value and value.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError('La foto no puede exceder 10MB.')
        return value