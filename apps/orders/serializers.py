"""
Serializers para pedidos, items, pagos y cotizaciones
"""
from rest_framework import serializers
from .models import Order, OrderItem, Payment, Quotation, PaymentStatus
from apps.products.serializers import ProductListSerializer
from apps.clients.serializers import ClientListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_detail = ProductListSerializer(source='product', read_only=True)
    scaled_bom = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_detail', 'quantity', 'servings', 'unit_price',
                  'custom_notes', 'bom_snapshot_scaled', 'scaled_bom', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'subtotal', 'scaled_bom']

    def get_scaled_bom(self, obj):
        return obj.scaled_bom

    def validate(self, attrs):
        # Validar que servings sea 12, 20 o 40
        if attrs.get('servings') not in [12, 20, 40]:
            raise serializers.ValidationError({'servings': 'Porciones deben ser 12, 20 o 40.'})

        # Validar stock si el pedido está por confirmarse
        if self.context.get('view') and self.context['view'].action == 'confirm':
            product = attrs['product']
            quantity = attrs.get('quantity', 1)
            servings = attrs.get('servings', 12)
            has_stock, shortages = product.check_stock_for_servings(servings, quantity)
            if not has_stock:
                raise serializers.ValidationError({'stock': f'Stock insuficiente: {shortages}'})

        return attrs


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'servings', 'unit_price', 'custom_notes']

    def validate_servings(self, value):
        if value not in [12, 20, 40]:
            raise serializers.ValidationError('Porciones deben ser 12, 20 o 40.')
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'method', 'status', 'transaction_id', 'notes', 'paid_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'paid_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['order', 'amount', 'method', 'notes']


class OrderSerializer(serializers.ModelSerializer):
    client_detail = ClientListSerializer(source='client', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    paid_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'client_detail', 'status', 'delivery_date', 'delivery_address',
                  'subtotal', 'discount', 'total', 'notes', 'items', 'payments',
                  'paid_amount', 'payment_status', 'confirmed_at', 'confirmed_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'subtotal', 'total', 'confirmed_at', 'confirmed_by', 'created_at', 'updated_at',
                           'paid_amount', 'payment_status']

    def get_paid_amount(self, obj):
        return sum(p.amount for p in obj.payments.filter(status=PaymentStatus.PAGADO_TOTAL))

    def get_payment_status(self, obj):
        paid = self.get_paid_amount(obj)
        if paid >= obj.total:
            return 'PAGADO_TOTAL'
        elif paid > 0:
            return 'PAGADO_PARCIAL'
        return 'PENDIENTE'


class OrderCreateUpdateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, required=False)

    class Meta:
        model = Order
        fields = ['client', 'status', 'delivery_date', 'delivery_address', 'discount', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            item_data['unit_price'] = item_data['product'].sale_price
            OrderItem.objects.create(order=order, **item_data)
        order.calculate_totals()
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                item_data['unit_price'] = item_data['product'].sale_price
                OrderItem.objects.create(order=instance, **item_data)
            instance.calculate_totals()
        return instance


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_detail = ClientListSerializer(source='client', read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'client_name', 'client_detail', 'status', 'delivery_date', 'total', 'items_count', 'items', 'payment_status', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Asegurar compatibilidad para templates que leen order.client.name u order.client como id
        if instance.client:
            ret['client'] = {
                'id': instance.client.id,
                'name': instance.client.name,
                'email': instance.client.email or '',
                'phone': instance.client.phone or '',
            }
        return ret

    def get_payment_status(self, obj):
        paid = sum(p.amount for p in obj.payments.all() if p.status in [PaymentStatus.PAGADO_TOTAL, PaymentStatus.PAGADO_PARCIAL])
        if paid >= obj.total:
            return 'PAGADO_TOTAL'
        elif paid > 0:
            return 'PAGADO_PARCIAL'
        return 'PENDIENTE'


class QuotationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_detail = ClientListSerializer(source='client', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Quotation
        fields = ['id', 'client', 'client_name', 'client_detail', 'items', 'valid_until', 'status',
                  'subtotal', 'discount', 'total', 'notes', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['subtotal', 'total', 'created_at', 'updated_at']


class QuotationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = ['client', 'items', 'valid_until', 'status', 'discount', 'notes']

    def validate_items(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Items debe ser una lista.')
        for item in value:
            required = ['product_id', 'quantity', 'servings', 'unit_price']
            for field in required:
                if field not in item:
                    raise serializers.ValidationError(f'Item requiere: {required}')
            if item['servings'] not in [12, 20, 40]:
                raise serializers.ValidationError('Porciones deben ser 12, 20 o 40.')
        return value