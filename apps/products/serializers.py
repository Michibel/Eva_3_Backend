"""
Serializers para productos, categorías y BOM con escalado por porciones
"""
from rest_framework import serializers
from .models import Category, Product, ProductImage, BOMItem


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order', 'is_active', 'products_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order', 'alt_text', 'created_at']
        read_only_fields = ['created_at']


class BOMItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    ingredient_unit_cost = serializers.DecimalField(source='ingredient.unit_cost', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = BOMItem
        fields = ['id', 'ingredient', 'ingredient_name', 'ingredient_unit', 'ingredient_unit_cost', 'quantity', 'unit', 'notes', 'order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class BOMItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOMItem
        fields = ['ingredient', 'quantity', 'unit', 'notes', 'order']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    bom_items = BOMItemSerializer(many=True, read_only=True)
    bom_calculated_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'category', 'category_name', 'name', 'description', 'image', 'base_price', 'sale_price',
                  'prep_time_minutes', 'base_servings', 'is_active', 'images', 'bom_items',
                  'bom_calculated_cost', 'profit_margin', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'bom_calculated_cost', 'profit_margin']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    bom_items = BOMItemCreateSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'image', 'base_price', 'sale_price',
                  'prep_time_minutes', 'base_servings', 'is_active', 'images', 'bom_items']

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        bom_items_data = validated_data.pop('bom_items', [])
        product = Product.objects.create(**validated_data)

        for img_data in images_data:
            ProductImage.objects.create(product=product, **img_data)

        for bom_data in bom_items_data:
            BOMItem.objects.create(product=product, **bom_data)

        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        bom_items_data = validated_data.pop('bom_items', None)

        instance = super().update(instance, validated_data)

        if images_data is not None:
            instance.images.all().delete()
            for img_data in images_data:
                ProductImage.objects.create(product=instance, **img_data)

        if bom_items_data is not None:
            instance.bom_items.all().delete()
            for bom_data in bom_items_data:
                BOMItem.objects.create(product=instance, **bom_data)

        return instance


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'category', 'category_name', 'name', 'base_servings', 'sale_price', 'is_active', 'created_at']


class BOMScaledSerializer(serializers.Serializer):
    """Serializer para BOM escalado"""
    ingredient_id = serializers.IntegerField()
    ingredient_name = serializers.CharField()
    ingredient_unit = serializers.CharField()
    base_quantity = serializers.DecimalField(max_digits=10, decimal_places=3)
    scaled_quantity = serializers.DecimalField(max_digits=10, decimal_places=3)
    unit = serializers.CharField()
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(allow_blank=True)


class ProductBOMScaleSerializer(serializers.Serializer):
    """Serializer para preview de BOM escalado"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    base_servings = serializers.IntegerField()
    target_servings = serializers.IntegerField()
    scale_factor = serializers.DecimalField(max_digits=5, decimal_places=3)
    bom_items = BOMScaledSerializer(many=True)
    total_estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=2)

    def to_representation(self, instance):
        # instance es un dict con los datos calculados
        return instance


class StockCheckSerializer(serializers.Serializer):
    """Serializer para verificación de stock"""
    has_stock = serializers.BooleanField()
    shortages = serializers.ListField(child=serializers.DictField())
    product_id = serializers.IntegerField()
    target_servings = serializers.IntegerField()
    quantity = serializers.IntegerField()