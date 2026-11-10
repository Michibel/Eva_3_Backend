"""
Views para productos con escalado BOM por porciones
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum
from .models import Category, Product, ProductImage, BOMItem
from .serializers import (
    CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer,
    ProductListSerializer, BOMItemSerializer, BOMItemCreateSerializer,
    BOMScaledSerializer, ProductBOMScaleSerializer, StockCheckSerializer
)


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(products_count=Count('products')).all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['order', 'name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('images', 'bom_items__ingredient').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'base_servings', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'base_price', 'sale_price', 'base_servings', 'created_at']
    ordering = ['category__order', 'name']

    def get_permissions(self):
        if self.action in ['favorites', 'toggle_favorite']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateUpdateSerializer
        elif self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    @action(detail=True, methods=['get'], url_path='bom-scaled')
    def bom_scaled(self, request, pk=None):
        """
        Preview del BOM escalado para porciones específicas.
        GET /api/v1/products/{id}/bom-scaled/?servings=20
        """
        product = self.get_object()
        target_servings = int(request.query_params.get('servings', product.base_servings))

        if target_servings not in [12, 20, 40]:
            return Response(
                {'detail': 'Porciones deben ser 12, 20 o 40.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        scaled_bom = product.get_scaled_bom(target_servings)
        total_cost = sum(item['estimated_cost'] for item in scaled_bom)
        scale_factor = target_servings / product.base_servings

        data = {
            'product_id': product.id,
            'product_name': product.name,
            'base_servings': product.base_servings,
            'target_servings': target_servings,
            'scale_factor': round(scale_factor, 3),
            'bom_items': scaled_bom,
            'total_estimated_cost': round(total_cost, 2),
        }
        serializer = ProductBOMScaleSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='stock-check')
    def stock_check(self, request, pk=None):
        """
        Verifica stock para producir cantidad x porciones.
        GET /api/v1/products/{id}/stock-check/?servings=20&quantity=5
        """
        product = self.get_object()
        target_servings = int(request.query_params.get('servings', product.base_servings))
        quantity = int(request.query_params.get('quantity', 1))

        has_stock, shortages = product.check_stock_for_servings(target_servings, quantity)

        data = {
            'has_stock': has_stock,
            'shortages': shortages,
            'product_id': product.id,
            'target_servings': target_servings,
            'quantity': quantity,
        }
        serializer = StockCheckSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='favorites')
    def favorites(self, request):
        """Productos favoritos del usuario"""
        user = request.user
        if not user.is_authenticated:
            return Response([])
        profile = getattr(user, 'profile', None)
        fav_ids = []
        if profile and isinstance(profile.preferences, dict):
            fav_ids = profile.preferences.get('favorite_products', [])
        products = Product.objects.filter(id__in=fav_ids, is_active=True).select_related('category')
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle_favorite')
    def toggle_favorite(self, request, pk=None):
        """Alternar favorito de un producto"""
        product = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return Response({'detail': 'Autenticación requerida'}, status=status.HTTP_401_UNAUTHORIZED)
        profile, _ = getattr(user.__class__, 'profile').related.related_model.objects.get_or_create(user=user)
        if not isinstance(profile.preferences, dict):
            profile.preferences = {}
        fav_ids = profile.preferences.get('favorite_products', [])
        if product.id in fav_ids:
            fav_ids.remove(product.id)
            is_favorite = False
        else:
            fav_ids.append(product.id)
            is_favorite = True
        profile.preferences['favorite_products'] = fav_ids
        profile.save()
        return Response({'status': 'ok', 'is_favorite': is_favorite, 'product_id': product.id})


class BOMItemViewSet(viewsets.ModelViewSet):
    queryset = BOMItem.objects.select_related('product', 'ingredient').all()
    serializer_class = BOMItemSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'ingredient']
    ordering = ['product', 'order']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            from .serializers import BOMItemCreateSerializer
            return BOMItemCreateSerializer
        return BOMItemSerializer