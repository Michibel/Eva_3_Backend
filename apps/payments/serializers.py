"""
Serializers para WebPay
"""
from rest_framework import serializers
from .models import WebPayTransaction
from apps.orders.serializers import OrderListSerializer


class WebPayTransactionSerializer(serializers.ModelSerializer):
    order_detail = OrderListSerializer(source='order', read_only=True)

    class Meta:
        model = WebPayTransaction
        fields = ['id', 'order', 'order_detail', 'buy_order', 'session_id', 'amount', 'status',
                  'token', 'response_code', 'authorization_code', 'payment_type_code',
                  'installments_number', 'response_json', 'return_url', 'final_url',
                  'created_at', 'confirmed_at']
        read_only_fields = fields


class WebPayInitSerializer(serializers.Serializer):
    """Serializer para iniciar transacción WebPay"""
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    return_url = serializers.URLField()

    def validate_order_id(self, value):
        from apps.orders.models import Order
        try:
            order = Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Pedido no encontrado.')
        if order.status not in [Order.OrderStatus.CONFIRMADO, Order.OrderStatus.EN_PRODUCCION, Order.OrderStatus.LISTO]:
            raise serializers.ValidationError('El pedido debe estar confirmado para pagar.')
        return value


class WebPayConfirmSerializer(serializers.Serializer):
    """Serializer para confirmar transacción WebPay (callback)"""
    token_ws = serializers.CharField()