"""
Serializers para clientes
"""
from rest_framework import serializers
from .models import Client, ClientPreference


class ClientPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPreference
        fields = ['id', 'key', 'value', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    preferences = ClientPreferenceSerializer(many=True, read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'address', 'notes', 'is_active', 'preferences', 'total_orders', 'total_spent', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_orders', 'total_spent']


class ClientCreateSerializer(serializers.ModelSerializer):
    preferences = ClientPreferenceSerializer(many=True, required=False)

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'address', 'notes', 'is_active', 'preferences']
        read_only_fields = ['id']

    def create(self, validated_data):
        preferences_data = validated_data.pop('preferences', [])
        client = Client.objects.create(**validated_data)
        for pref_data in preferences_data:
            ClientPreference.objects.create(client=client, **pref_data)
        return client

    def update(self, instance, validated_data):
        preferences_data = validated_data.pop('preferences', None)
        instance = super().update(instance, validated_data)
        if preferences_data is not None:
            instance.preferences.all().delete()
            for pref_data in preferences_data:
                ClientPreference.objects.create(client=instance, **pref_data)
        return instance


class ClientListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    orders_count = serializers.IntegerField(source='total_orders', read_only=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    last_order_date = serializers.DateTimeField(read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'is_active', 'created_at', 'orders_count', 'total_spent', 'last_order_date', 'user']

    def get_user(self, obj):
        if obj.user:
            return {'username': obj.user.username}
        return None