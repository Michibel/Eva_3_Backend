"""
Serializers para ingredientes, stock y compras
"""
from rest_framework import serializers
from .models import Supplier, Ingredient, StockMovement, PurchaseOrder, PurchaseOrderItem


class SupplierSerializer(serializers.ModelSerializer):
    ingredients_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact', 'phone', 'email', 'address', 'is_active', 'ingredients_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class IngredientSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    stock_status = serializers.CharField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'unit', 'current_stock', 'min_stock', 'unit_cost', 'supplier', 'supplier_name',
                  'is_perishable', 'shelf_life_days', 'is_active', 'stock_status', 'is_low_stock', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'stock_status', 'is_low_stock']


class IngredientCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['name', 'unit', 'current_stock', 'min_stock', 'unit_cost', 'supplier', 'is_perishable', 'shelf_life_days', 'is_active']


class IngredientListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'unit', 'current_stock', 'min_stock', 'unit_cost', 'stock_status', 'is_active']


class StockMovementSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = StockMovement
        fields = ['id', 'ingredient', 'ingredient_name', 'ingredient_unit', 'type', 'quantity', 'reference', 'notes', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_at']


class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['ingredient', 'type', 'quantity', 'reference', 'notes']

    def validate(self, attrs):
        if attrs['type'] in ['SALIDA', 'MERMA']:
            ingredient = attrs['ingredient']
            if ingredient.current_stock < attrs['quantity']:
                raise serializers.ValidationError(f"Stock insuficiente. Disponible: {ingredient.current_stock} {ingredient.unit}")
        return attrs


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'ingredient', 'ingredient_name', 'ingredient_unit', 'quantity', 'unit_cost', 'received_quantity', 'subtotal', 'notes']
        read_only_fields = ['received_quantity', 'subtotal']


class PurchaseOrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['ingredient', 'quantity', 'unit_cost', 'notes']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'supplier', 'supplier_name', 'expected_date', 'status', 'total', 'notes', 'items', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['total', 'created_at', 'updated_at']


class PurchaseOrderCreateUpdateSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemCreateSerializer(many=True, required=False)

    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'expected_date', 'status', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(order=order, **item_data)
        order.update_total()
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseOrderItem.objects.create(order=instance, **item_data)
            instance.update_total()
        return instance